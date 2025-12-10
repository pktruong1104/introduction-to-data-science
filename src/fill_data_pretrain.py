from __future__ import annotations

from pathlib import Path
from typing import Set, List, Dict, Tuple
import warnings

import numpy as np
import pandas as pd
from tqdm import tqdm

# Tắt warning assignment copy của pandas để log sạch hơn
pd.options.mode.chained_assignment = None


def _clean_combo_str(s) -> Set[str]:
    """
    Chuyển chuỗi tổ hợp thành Set các khối.
    Xử lý: "A00; A01 ; " -> {'A00', 'A01'}
    """
    if pd.isna(s):
        return set()
    s = str(s).strip()
    if not s:
        return set()
    # Tách bằng dấu ; và loại bỏ khoảng trắng thừa
    parts = [p.strip().upper() for p in s.split(";") if p.strip()]
    return set(parts)


def _set_to_str(s: Set[str]) -> str:
    """Chuyển Set về string chuẩn để lưu vào CSV."""
    if not s:
        return ""
    return ";".join(sorted(s))


def _calculate_jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    """Tính chỉ số Jaccard Similarity giữa 2 tập hợp."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _fill_score_logic(
    target_anchor_combos: Set[str],
    donors: List[dict],
    global_mean: float
) -> float:
    """
    Tính toán điểm chuẩn dựa trên logic ưu tiên:
    1. Chính xác (Exact Match): Mean của các donor trùng khớp hoàn toàn tổ hợp.
    2. Tương đồng (Jaccard Weighted): Trung bình có trọng số.
    3. Global Mean: Fallback cuối cùng.
    
    donors: List các dict {'score': float, 'combos': Set[str]}
    """
    if not donors:
        return global_mean

    # --- Ưu tiên 1: Tìm các dòng trùng khớp EXACT tổ hợp ---
    exact_matches = [
        d['score'] for d in donors 
        if d['combos'] == target_anchor_combos
    ]
    if exact_matches:
        return np.mean(exact_matches)

    # --- Ưu tiên 2: Tính trọng số Jaccard ---
    weights = []
    scores = []
    
    for d in donors:
        w = _calculate_jaccard(d['combos'], target_anchor_combos)
        weights.append(w)
        scores.append(d['score'])
    
    total_weight = sum(weights)
    
    # Nếu tổng trọng số > 0 (có sự liên quan về tổ hợp)
    if total_weight > 0:
        weighted_sum = sum(w * s for w, s in zip(weights, scores))
        return weighted_sum / total_weight
    
    # Nếu tất cả Jaccard = 0 (cùng nhóm ngành nhưng khác hẳn khối thi)
    # -> Dùng trung bình thường của nhóm (group mean) thay vì global mean
    # vì dù sao cũng cùng trường/ngành.
    return np.mean(scores)


def fill_data_pretrain(input_csv: str | Path, output_csv: str | Path) -> pd.DataFrame:
    input_csv = Path(input_csv)
    output_csv = Path(output_csv)

    print(f"Đang đọc dữ liệu từ {input_csv}...")
    df = pd.read_csv(input_csv)

    # Xác định cột
    years = range(2019, 2025) # 2019..2024
    fill_years = range(2019, 2024) # 2019..2023

    # 1. Tiền xử lý dữ liệu số học và chuỗi cơ bản
    print("Tiền xử lý dữ liệu...")
    
    # Convert điểm chuẩn sang số (coercing errors)
    for y in years:
        col = f"Điểm chuẩn năm {y}"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # --- MỚI: Lọc bỏ các dòng thiếu dữ liệu năm 2024 (Anchor) ---
    print("Đang lọc bỏ các dòng thiếu dữ liệu năm 2024...")
    initial_rows = len(df)
    
    # Lọc 1: Điểm chuẩn 2024 phải khác NaN
    df = df[df["Điểm chuẩn năm 2024"].notna()]
    
    # Lọc 2: Tổ hợp 2024 phải có nội dung (không rỗng)
    # Sử dụng list comprehension để check nhanh thay vì apply
    valid_combo_mask = [bool(_clean_combo_str(x)) for x in df["Tổ hợp môn năm 2024"]]
    df = df[valid_combo_mask]
    
    dropped_rows = initial_rows - len(df)
    print(f"-> Đã loại bỏ {dropped_rows} dòng không có anchor 2024. Còn lại: {len(df)} dòng.")

    # --- QUAN TRỌNG: Reset index SAU KHI LỌC để đảm bảo index là duy nhất và liên tục ---
    df = df.reset_index(drop=True)
    
    # Tạo cột Base Group
    # Lưu ý: Ép kiểu string trước khi split để tránh lỗi nếu cột Mã ngành đang là int
    df["_group_id"] = (
        df["Mã trường"].astype(str).str.strip() + "_" + 
        df["Mã ngành"].astype(str).str.split("*").str[0].str.strip()
    )

    # 2. Tính Global Mean cho từng năm (Backup plan)
    global_means = {}
    for y in fill_years:
        col_score = f"Điểm chuẩn năm {y}"
        if col_score in df.columns:
            global_means[y] = df[col_score].mean()
        else:
            global_means[y] = 0.0

    # 3. Xử lý theo từng Group
    # Nhóm theo _group_id
    grouped = df.groupby("_group_id")
    
    print(f"Bắt đầu fill dữ liệu cho {len(grouped)} nhóm ngành...")
    
    # List để thu thập các update (tránh update trực tiếp quá nhiều lần làm chậm)
    # Tuy nhiên với logic phức tạp phụ thuộc lẫn nhau, update trực tiếp df an toàn hơn về logic
    # nhưng ta cần cẩn thận không dùng dữ liệu "vừa fill" để fill cho dòng khác cùng năm
    # -> dùng dữ liệu gốc (snapshot) để tìm donor.
    
    for group_name, group_df in tqdm(grouped, desc="Processing Groups"):
        # group_df là DataFrame con của nhóm hiện tại
        # Lấy index thực tế của nhóm
        idxs = group_df.index
        
        # Lấy snapshot dữ liệu gốc của nhóm này (chỉ đọc)
        # Để đảm bảo donor luôn là dữ liệu thực (real data), không phải dữ liệu fake vừa fill
        group_df_orig = group_df.copy()
        
        # Lọc ra các dòng "Target" trong nhóm
        # Vì đã lọc toàn bộ DF từ đầu, nên TẤT CẢ các dòng còn lại đều là Target hợp lệ
        targets = []
        for idx in idxs:
            th24 = _clean_combo_str(df.at[idx, "Tổ hợp môn năm 2024"])
            # th24 chắc chắn không rỗng vì đã lọc ở trên
            targets.append((idx, th24)) 
        
        if not targets:
            continue

        # Cache tổ hợp của cả nhóm cho từng năm để dùng cho logic Union
        # (Union của TẤT CẢ tổ hợp Y trong group)
        group_combos_by_year = {}
        for y in fill_years:
            col_th = f"Tổ hợp môn năm {y}"
            if col_th not in df.columns: continue
            
            # Lấy tất cả combo có trong cột này của nhóm
            all_combos = set()
            raw_vals = group_df_orig[col_th].dropna()
            for val in raw_vals:
                all_combos.update(_clean_combo_str(val))
            group_combos_by_year[y] = all_combos

        # --- Bắt đầu Fill cho từng Target ---
        for target_idx, anchor_combos in targets:
            
            for y in fill_years:
                col_th_y = f"Tổ hợp môn năm {y}"
                col_sc_y = f"Điểm chuẩn năm {y}"
                
                # --- LOGIC 1: FILL TỔ HỢP (UNION) ---
                # Lấy tổ hợp hiện tại của dòng target (nếu có)
                current_combos = _clean_combo_str(df.at[target_idx, col_th_y])
                
                # Lấy tổ hợp của toàn group năm đó
                group_combos = group_combos_by_year.get(y, set())
                
                # Union: Hiện tại | Anchor 2024 | Toàn bộ Group năm Y
                final_combos = current_combos | anchor_combos | group_combos
                
                # Cập nhật vào DataFrame
                df.at[target_idx, col_th_y] = _set_to_str(final_combos)
                
                # --- LOGIC 2: FILL ĐIỂM CHUẨN ---
                current_score = df.at[target_idx, col_sc_y]
                
                # Nếu đã có điểm -> giữ nguyên (theo yêu cầu)
                if pd.notna(current_score):
                    continue
                
                # Tìm Donors từ snapshot gốc (group_df_orig)
                # Donor là dòng có Tổ hợp != rỗng VÀ Điểm != NaN ở năm Y
                donors = []
                # Lấy dữ liệu raw từ numpy array để tăng tốc thay vì iterrows
                valid_donors_mask = (
                    group_df_orig[col_th_y].notna() & 
                    (group_df_orig[col_th_y].str.strip() != "") &
                    group_df_orig[col_sc_y].notna()
                )
                valid_donors_df = group_df_orig[valid_donors_mask]
                
                for _, row in valid_donors_df.iterrows():
                    d_combos = _clean_combo_str(row[col_th_y])
                    if d_combos: # Double check
                        donors.append({
                            'score': float(row[col_sc_y]),
                            'combos': d_combos
                        })
                
                # Tính toán điểm fill
                filled_val = _fill_score_logic(
                    target_anchor_combos=anchor_combos,
                    donors=donors,
                    global_mean=global_means.get(y, 0.0)
                )
                
                df.at[target_idx, col_sc_y] = round(filled_val, 2)

    # Dọn dẹp cột tạm
    df = df.drop(columns=["_group_id"])
    
    # Lưu file
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Hoàn tất! File đã lưu tại: {output_csv}")
    
    return df

if __name__ == "__main__":
    # Test block
    # Giả sử bạn chạy file này trực tiếp
    import sys
    
    # Thiết lập đường dẫn tương đối để test nếu cần
    cur_dir = Path(__file__).parent
    data_in = cur_dir.parent / "data" / "data_pretrain.csv"
    data_out = cur_dir.parent / "data" / "data_pretrain_filled_v2.csv"
    
    if data_in.exists():
        fill_data_pretrain(data_in, data_out)
    else:
        print(f"Không tìm thấy file input tại {data_in}")