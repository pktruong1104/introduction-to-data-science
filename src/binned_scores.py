# src/binned_scores.py

import pandas as pd
import numpy as np
from pathlib import Path

# Các môn sẽ xử lý
SUBJECTS = [
    "Toán",
    "Văn",
    "Ngoại ngữ",
    "Lí",
    "Hóa",
    "Sinh",
    "Sử",
    "Địa",
    "GDCD",
]


# ===============================
# 1. Đọc & gộp dữ liệu thô
# ===============================
def load_exam_data(data_dir=".", years=range(2019, 2025)) -> pd.DataFrame:
    """
    Đọc các file diem_thi_toan_quoc_YYYY.csv trong data_dir,
    chỉ lấy cột NĂM_THI + các cột điểm trong SUBJECTS.

    Trả về: DataFrame có cột NĂM_THI + SUBJECTS (đã ép về numeric).
    """
    data_dir = Path(data_dir)
    dfs = []

    usecols = ["NĂM_THI"] + SUBJECTS

    for year in years:
        file = data_dir / f"diem_thi_toan_quoc_{year}.csv"
        if not file.exists():
            print(f"⚠️ Không tìm thấy file: {file}, bỏ qua.")
            continue

        print(f"Đang đọc: {file}")
        try:
            # cố gắng chỉ đọc cột mình cần
            df = pd.read_csv(
                file,
                usecols=usecols,
                low_memory=False,
            )
        except ValueError:
            # trường hợp file thiếu 1 số cột → đọc full rồi lọc
            raw = pd.read_csv(file, low_memory=False)
            available = [c for c in usecols if c in raw.columns]
            missing = [c for c in usecols if c not in raw.columns]
            if missing:
                print(f"⚠️ File {file.name} thiếu cột: {missing}")
            df = raw[available]

        if "NĂM_THI" not in df.columns:
            df["NĂM_THI"] = year

        dfs.append(df)

    if not dfs:
        raise FileNotFoundError(
            "Không đọc được file CSV nào. Kiểm tra lại data_dir & years."
        )

    data = pd.concat(dfs, ignore_index=True)
    data["NĂM_THI"] = data["NĂM_THI"].astype(int)

    # Ép cột điểm sang số (xử lý cả trường hợp dùng dấu phẩy)
    for col in SUBJECTS:
        if col in data.columns:
            col_str = data[col].astype(str).str.replace(",", ".", regex=False)
            data[col] = pd.to_numeric(col_str, errors="coerce")
        else:
            print(f"⚠️ Không thấy cột điểm: {col}")

    return data


# ===============================
# 2. Hàm tạo edges (mốc biên) theo môn
# ===============================
def build_edges(subject: str) -> np.ndarray:
    """
    Toán, Ngoại ngữ: step = 0.2  -> [0,0.2], (0.2,0.4], ..., (9.8,10]
    Môn khác:        step = 0.25 -> [0,0.25],(0.25,0.5],...,(9.75,10]
    """
    if subject in ("Toán", "Ngoại ngữ"):
        step = 0.2
    else:
        step = 0.25

    n_bins = int(10 / step)
    edges = np.linspace(0, 10, n_bins + 1)  # 0..10 inclusive
    return edges


# ===============================
# 3. Tạo bảng bin gọn
# ===============================
def build_binned_table(
    data: pd.DataFrame,
    subjects=SUBJECTS,
) -> pd.DataFrame:
    """
    Từ DataFrame raw (NĂM_THI + điểm), tạo bảng bin:

        nam_thi, mon, bin_start, bin_end, count

    Mỗi dòng = 1 (năm, môn, khoảng điểm) với count > 0.
    """
    rows = []
    years = sorted(data["NĂM_THI"].dropna().unique())

    for subject in subjects:
        if subject not in data.columns:
            print(f"⚠️ Không thấy cột {subject}, bỏ qua.")
            continue

        print(f"Tính bin cho môn: {subject}")
        edges = build_edges(subject)

        # chỉ giữ 2 cột cần cho môn này để nhẹ RAM
        subj_df = data[["NĂM_THI", subject]].dropna()

        for year in years:
            scores = subj_df.loc[subj_df["NĂM_THI"] == year, subject].dropna()
            if scores.empty:
                continue

            # cắt bin [0, step], (step, 2*step], ...
            cats = pd.cut(
                scores,
                bins=edges,
                right=True,
                include_lowest=True,
            )

            counts = cats.value_counts().sort_index()

            for interval, count in counts.items():
                if count == 0:
                    continue  # không ghi những bin không có thí sinh

                rows.append(
                    {
                        "nam_thi": int(year),
                        "mon": subject,
                        "bin_start": float(interval.left),
                        "bin_end": float(interval.right),
                        "count": int(count),
                    }
                )

    binned_df = pd.DataFrame(
        rows, columns=["nam_thi", "mon", "bin_start", "bin_end", "count"]
    )
    return binned_df


# ===============================
# 4. Hàm export ra CSV (dùng được cả trong notebook)
# ===============================
def export_binned_csv(
    data_dir=".",
    years=range(2019, 2025),
    out_path="diem_thi_binned_2019_2024.csv",
) -> pd.DataFrame:
    """
    Đọc dữ liệu thô, bin điểm theo năm + môn, rồi ghi ra 1 CSV gọn.

    Trả về: DataFrame binned (để dùng luôn trong notebook nếu muốn).
    """
    data = load_exam_data(data_dir=data_dir, years=years)
    binned = build_binned_table(data, subjects=SUBJECTS)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    binned.to_csv(out_path, index=False)
    print(f"✅ Đã lưu bảng bin vào: {out_path}")
    print("Số dòng:", len(binned))

    return binned


# ===============================
# 5. Chạy trực tiếp file (tùy chọn)
# ===============================
if __name__ == "__main__":
    # Khi chạy: python src/binned_scores.py
    export_binned_csv(
        data_dir=".",                      # thư mục chứa các CSV gốc
        years=range(2019, 2025),
        out_path="diem_thi_binned_2019_2024.csv",
    )
