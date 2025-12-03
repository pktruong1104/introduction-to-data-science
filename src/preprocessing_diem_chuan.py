from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Optional, List

import pandas as pd


# ==========================
# Đường dẫn cơ bản
# ==========================

# Thư mục src/
SRC_DIR = Path(__file__).resolve().parent
# Thư mục project_root/ (cha của src)
BASE_DIR = SRC_DIR.parent


# ==========================
# Hàm chính: build bảng ngành wide
# ==========================

def build_nganh_training_dataset(
    input_csv: str,
    output_csv: str,
    year_from: int = 2019,
    year_to: int = 2025,
) -> None:
    """
    Từ diem_chuan_chuan_hoa.csv (dạng long):

        Mã trường | Mã ngành | Tên ngành | Tổ hợp môn | Điểm chuẩn | Năm xét tuyển | Ghi chú

    -> Tạo bảng wide có dạng:

        Mã trường, Mã ngành, Tên ngành,
        Tổ hợp môn năm 2019, Điểm chuẩn năm 2019,
        ...,
        Tổ hợp môn năm 2025, Điểm chuẩn năm 2025.

    Đảm bảo (Mã trường, Mã ngành, Tên ngành) là khóa chính (mỗi ngành 1 dòng).
    """

    df = pd.read_csv(input_csv)

    required_cols = [
        "Mã trường",
        "Mã ngành",
        "Tên ngành",
        "Tổ hợp môn",
        "Điểm chuẩn",
        "Năm xét tuyển",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu các cột bắt buộc trong {input_csv}: {missing}")

    # Chuẩn hóa kiểu dữ liệu năm
    df["Năm xét tuyển"] = pd.to_numeric(df["Năm xét tuyển"], errors="coerce").astype("Int64")

    # Lọc theo khoảng năm muốn dùng
    df = df[df["Năm xét tuyển"].between(year_from, year_to)]
    if df.empty:
        raise ValueError(
            f"Không có dữ liệu nào trong khoảng năm {year_from}–{year_to} "
            f"trong file {input_csv}"
        )

    base_cols = ["Mã trường", "Mã ngành"]

    # Gộp trước theo (Mã trường, Mã ngành, Tên ngành, Năm xét tuyển)
    # để đảm bảo mỗi (ngành, năm) là 1 record duy nhất.
    grouped = (
        df.groupby(base_cols + ["Năm xét tuyển"], as_index=False)
        .agg({
            # Nếu 1 ngành-năm có nhiều tổ hợp -> nối lại bằng '; '
            "Tổ hợp môn": lambda x: "; ".join(sorted({str(v).strip() for v in x if pd.notna(v)})),
            # Điểm chuẩn: chọn max (có thể đổi thành 'first' nếu bạn muốn)
            "Điểm chuẩn": "max",
        })
    )

    # Pivot sang dạng wide
    pivot = grouped.pivot_table(
        index=base_cols,
        columns="Năm xét tuyển",
        values=["Tổ hợp môn", "Điểm chuẩn"],
        aggfunc="first",  # sau groupby mỗi ô đã unique
    )

    # Làm phẳng MultiIndex columns -> "Tổ hợp môn năm 2019", "Điểm chuẩn năm 2019", ...
    pivot.columns = [
        f"{col_name} năm {int(year)}"
        for col_name, year in pivot.columns
    ]

    pivot = pivot.reset_index()

    # Đảm bảo có đủ cột cho mọi năm trong [year_from, year_to]
    expected_years: List[int] = list(range(year_from, year_to + 1))
    for year in expected_years:
        for base_name in ["Tổ hợp môn", "Điểm chuẩn"]:
            col = f"{base_name} năm {year}"
            if col not in pivot.columns:
                pivot[col] = pd.NA

    # Sắp xếp lại thứ tự cột: khóa chính trước, rồi theo năm tăng dần
    ordered_cols = (
        base_cols
        + [f"Tổ hợp môn năm {y}" for y in expected_years]
        + [f"Điểm chuẩn năm {y}" for y in expected_years]
    )

    pivot = pivot[ordered_cols]

    # Ghi file
    pivot.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Đã tạo training dataset: {output_csv}")


# ==========================
# Hàm default dùng đường dẫn project
# ==========================

def build_nganh_training_dataset_default() -> None:
    """
    Dùng đường dẫn mặc định:

        input : data/diem_chuan_chuan_hoa.csv
        output: data/data_pretrain.csv
    """
    data_dir = BASE_DIR / "data"
    input_path = data_dir / "diem_chuan_chuan_hoa.csv"
    output_path = data_dir / "data_pretrain.csv"

    if not input_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file input: {input_path}\n"
            "Hãy chắc rằng file nằm ở: project_root/data/diem_chuan_chuan_hoa.csv"
        )

    build_nganh_training_dataset(str(input_path), str(output_path))


# Cho phép chạy trực tiếp: python -m src.preprocessing_diem_chuan
if __name__ == "__main__":
    build_nganh_training_dataset_default()
