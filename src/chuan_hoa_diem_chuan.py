import re
import pandas as pd
import unicodedata
from pathlib import Path


# ==========================
# Helpers cơ bản
# ==========================

def remove_accents(s: str):
    """Bỏ dấu tiếng Việt, dùng nếu cần chuẩn hóa."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def extract_to_hop(raw: str) -> str:
    """
    Nhận chuỗi Tổ hợp môn (có thể có ngoặc, khoảng trắng, dấu phân tách khác nhau)
    Trả về chuỗi chuẩn: TOÁN;ANH;C03;C04;GDKTPL
    """
    if raw is None or raw == "":
        return ""
    s = str(raw).strip()
    s = re.sub(r"\s+", " ", s)  # Gom khoảng trắng thừa

    # Nếu có ngoặc thì giữ nguyên cấu trúc chuỗi (chỉ xử lý khoảng trắng)
    if "(" in s or ")" in s:
        s = re.sub(r"\s+\(", "(", s)
        s = re.sub(r"\)\s+", ")", s)
        s = re.sub(r"\(\s+", "(", s)
        s = re.sub(r"\s+\)", ")", s)
        return s.strip()

    # Chuẩn hóa các dấu phân tách thành ';'
    parts = re.split(r"[;,/|]+", s)
    parts = [p.strip() for p in parts if p.strip()]
    return ";".join(parts)


def normalize_major_code_logic_substring(current_code, last_valid_base, ma_truong=None):
    """
    - Nếu mã ngành BẮT ĐẦU bằng mã trường → giữ nguyên, không chạy logic 7 số.
    - Nếu chứa chuỗi 7 chữ số → dùng làm base.
    - Nếu không → ghép base trước đó.
    """
    ma = str(current_code).strip()
    if not ma or ma.lower() == "nan":
        return "", last_valid_base

    # Nếu mã ngành bắt đầu bằng mã trường
    if ma_truong and isinstance(ma_truong, str):
        mt = ma_truong.strip().upper()
        if ma.upper().startswith(mt):
            return ma, last_valid_base

    # Tách 7 chữ số làm base
    match = re.search(r"(\d{7})", ma)
    if match:
        new_base = match.group(1)
        return ma, new_base

    # Không có 7 số thì ghép base cũ
    if last_valid_base:
        if ma.startswith("_"):
            return f"{last_valid_base}{ma}", last_valid_base
        else:
            return f"{last_valid_base}_{ma}", last_valid_base

    # Không có base → trả về nguyên
    return ma, last_valid_base


def remove_whitespace_major(code: str) -> str:
    """Xóa tất cả khoảng trắng trong mã ngành."""
    if not isinstance(code, str) or not code:
        return code
    return code.replace(" ", "")


# ==========================
# Chuẩn hóa tên ngành
# ==========================

def chuan_hoa_ten_nganh(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa Tên ngành theo:
    - Nhóm các dòng cùng Mã ngành
    - Lấy tên ngành xuất hiện nhiều nhất (mode) cho toàn bộ group đó
    """
    def get_mode(series: pd.Series) -> str:
        counts = series.value_counts()
        if counts.empty:
            return ""
        return counts.idxmax()

    df["Tên ngành"] = (
        df.groupby(["Mã ngành"])["Tên ngành"]
          .transform(get_mode)
    )
    return df


# ==========================
# Lọc ngành đủ năm 2019–2024
# ==========================

def filter_major_full_years(df_clean: pd.DataFrame, path_loai) -> pd.DataFrame:
    """
    Lọc ra các mã ngành (theo Mã trường + Mã ngành) có đủ
    toàn bộ các năm 2019 → 2024.
    Đồng thời lưu các hàng bị loại vào file CSV.
    """
    REQUIRED_YEARS = {2019, 2020, 2021, 2022, 2023, 2024}
    path_loai = Path(path_loai)

    # Xác định các nhóm hợp lệ
    valid_groups = df_clean.groupby(
        ["Mã trường", "Mã ngành"]
    )["Năm xét tuyển"].apply(
        lambda years: REQUIRED_YEARS.issubset(set(years))
    )
    valid_indices = valid_groups[valid_groups].index

    # DataFrame cuối cùng chỉ chứa các nhóm hợp lệ
    df_final = (
        df_clean.set_index(["Mã trường", "Mã ngành"])
                .loc[valid_indices]
                .reset_index()
                .sort_values(by=["Mã trường", "Mã ngành", "Năm xét tuyển"])
    )

    # Lưu các hàng bị loại
    df_removed = (
        df_clean.set_index(["Mã trường", "Mã ngành"])
                .drop(valid_indices)
                .reset_index()
    )
    df_removed.to_csv(path_loai, index=False, encoding="utf-8-sig")

    return df_final


# ==========================
# Tách ngành_khối
# ==========================

def apply_major_khoi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chỉ tách thành mã ngành_khối khi:
        - Cùng Mã trường
        - Cùng Mã ngành
        - Cùng Năm xét tuyển
        - Có >= 2 tổ hợp môn
    """
    group_counts = (
        df.groupby(["Mã trường", "Mã ngành", "Năm xét tuyển"])["Tổ hợp môn"]
        .nunique()
    )

    multi_keys = set(group_counts[group_counts > 1].index)
    result_rows = []

    for _, r in df.iterrows():
        key = (r["Mã trường"], r["Mã ngành"], r["Năm xét tuyển"])
        khoi_list = str(r["Tổ hợp môn"]).split(";") if r["Tổ hợp môn"] else [""]

        if key in multi_keys:
            for khoi in khoi_list:
                result_rows.append({
                    **r.to_dict(),
                    "Mã ngành": f"{r['Mã ngành']}_{khoi}",
                    "Tổ hợp môn": khoi,
                })
        else:
            result_rows.append(r.to_dict())

    return pd.DataFrame(result_rows)


# ==========================
# Điền missing theo năm gần nhất
# ==========================

def fill_missing_nearest_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Điền Tên ngành / Tổ hợp môn bị rỗng dựa trên:
    - ưu tiên Tổ hợp môn của năm liền trước nếu có
    - nếu không có thì chọn năm gần nhất (trước hoặc sau)
    - nếu nhiều năm cùng gần thì ưu tiên năm lớn hơn
    """
    filled_rows = []

    for (school, major), group in df.groupby(["Mã trường", "Mã ngành"]):
        group_sorted = group.sort_values("Năm xét tuyển")
        years = group_sorted["Năm xét tuyển"].tolist()

        name_map = dict(zip(years, group_sorted["Tên ngành"]))
        tohop_map = dict(zip(years, group_sorted["Tổ hợp môn"]))

        updated_rows = []

        for _, row in group_sorted.iterrows():
            year = row["Năm xét tuyển"]
            name = str(row["Tên ngành"]).strip()
            tohop = str(row["Tổ hợp môn"]).strip()

            # Nếu đầy đủ thì giữ nguyên
            if name and tohop:
                updated_rows.append(row)
                continue

            # Ưu tiên lấy tổ hợp của năm liền trước
            if not tohop:
                prev_year = year - 1
                prev_tohop = str(tohop_map.get(prev_year, "")).strip()
                if prev_tohop:
                    row["Tổ hợp môn"] = prev_tohop
                    tohop = prev_tohop

            # Nếu vẫn thiếu thì tìm năm gần nhất
            if not name or not tohop:
                candidates = [
                    y for y in years
                    if y != year and (
                        str(name_map.get(y, "")).strip()
                        or str(tohop_map.get(y, "")).strip()
                    )
                ]

                if candidates:
                    min_dist = min(abs(y - year) for y in candidates)
                    nearest_years = [y for y in candidates if abs(y - year) == min_dist]

                    chosen_year = max(nearest_years)

                    if not name:
                        row["Tên ngành"] = name_map.get(chosen_year, "")
                    if not tohop:
                        row["Tổ hợp môn"] = tohop_map.get(chosen_year, "")

            updated_rows.append(row)

        filled_rows.extend(updated_rows)

    return pd.DataFrame(filled_rows)


# ==========================
# HÀM CHÍNH: Gọi từ notebook
# ==========================

def process_diem_chuan(path_input, path_output, path_removed):
    """
    Chuẩn hóa dữ liệu điểm chuẩn:

    - path_input:  CSV gốc (diem_chuan_all.csv)
    - path_output: CSV chuẩn hóa (diem_chuan_chuan_hoa.csv)
    - path_removed: CSV lưu các ngành bị loại (không đủ 2019–2024)
    """
    path_input = Path(path_input)
    path_output = Path(path_output)
    path_removed = Path(path_removed)

    print(f"Đang đọc dữ liệu từ: {path_input}")
    try:
        df = pd.read_csv(path_input, dtype=str).fillna("")
    except FileNotFoundError:
        print("Không tìm thấy file input.")
        return None

    clean_rows = []
    current_base_id = ""

    # 1) Chuẩn hóa từng dòng
    for _, r in df.iterrows():
        ma_raw = r.get("Mã ngành", "")
        ma_raw = remove_whitespace_major(ma_raw)

        ten = r.get("Tên ngành", "")
        tohop = extract_to_hop(r.get("Tổ hợp môn", ""))
        score = r.get("Điểm chuẩn", "")
        school = r.get("Mã trường", "")
        ghichu = r.get("Ghi chú", "")

        ma_final, new_base = normalize_major_code_logic_substring(
            ma_raw, current_base_id, school
        )
        if new_base:
            current_base_id = new_base

        # Năm xét tuyển
        y_match = re.search(r"20\d{2}", str(r.get("Năm xét tuyển", "")))
        year = int(y_match.group(0)) if y_match else 0

        clean_rows.append({
            "Mã trường": school,
            "Mã ngành": ma_final,
            "Tên ngành": ten,
            "Tổ hợp môn": tohop,
            "Điểm chuẩn": score,
            "Năm xét tuyển": year,
            "Ghi chú": ghichu,
        })

    df_clean = pd.DataFrame(clean_rows)

    # Điền missing
    df_clean = fill_missing_nearest_year(df_clean)

    # Lọc ngành có đủ các năm 2019–2024
    print("Đang lọc các ngành có đủ dữ liệu từ 2019 đến 2024...")
    df_clean = filter_major_full_years(df_clean, path_removed)

    # Chuẩn hóa tên ngành
    df_clean = chuan_hoa_ten_nganh(df_clean)

    # Tách ngành_khối
    df_final = apply_major_khoi(df_clean)

    # Ghi output
    df_final.to_csv(path_output, index=False, encoding="utf-8-sig")
    print(f"Hoàn tất! File lưu tại: {path_output}")

    return df_final
