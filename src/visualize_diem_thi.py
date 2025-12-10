# src/visualize_diem_thi.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# nếu muốn dùng lại SUBJECTS từ binned_scores thì có thể import:
# from binned_scores import SUBJECTS

# Ở đây define lại cho độc lập, đỡ bị import vòng
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
# 1. (OPTION) Đọc bảng bin từ CSV
# ===============================
def load_binned_scores(path) -> pd.DataFrame:
    """
    Đọc bảng bin từ CSV có cột:
        nam_thi, mon, bin_start, bin_end, count
    """
    path = Path(path)
    df = pd.read_csv(path)

    expected_cols = {"nam_thi", "mon", "bin_start", "bin_end", "count"}
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"File {path} thiếu cột: {missing}")

    return df


# ===============================
# 2. Xử lý bin & label
# ===============================
def _build_bins_and_labels(df_sub: pd.DataFrame):
    """
    Từ subset cho 1 môn, tạo:
      - bins: list[(start, end)] đã sort
      - centers: np.ndarray tâm mỗi bin
      - labels: list[str] dạng [a,b] / (a,b]
    """
    unique_bins = (
        df_sub[["bin_start", "bin_end"]]
        .drop_duplicates()
        .sort_values(["bin_start", "bin_end"])
    )

    bins = list(unique_bins.itertuples(index=False, name=None))  # [(start, end), ...]

    if not bins:
        return [], np.array([]), []

    centers = []
    labels = []
    first_start = bins[0][0]

    for start, end in bins:
        center = (start + end) / 2.0
        centers.append(center)

        if start == first_start:
            label = f"[{start:.2f}, {end:.2f}]"
        else:
            label = f"({start:.2f}, {end:.2f}]"

        labels.append(label.replace(".00", ""))  # gọn hơn: [0, 0.25]

    return bins, np.array(centers), labels


# ===============================
# 3. Ước lượng mean/median từ bảng bin
# ===============================
def _approx_stats_from_binned(bin_centers: np.ndarray, counts: np.ndarray):
    """
    Tính xấp xỉ mean, median, n từ bảng bin.
    (coi tất cả điểm trong bin nằm tại tâm bin)
    """
    n = int(counts.sum())
    if n == 0:
        return np.nan, np.nan, 0

    mean = float((bin_centers * counts).sum() / n)

    cum_counts = counts.cumsum()
    half = n / 2.0
    median_idx = int(np.searchsorted(cum_counts, half))
    if median_idx >= len(bin_centers):
        median_idx = len(bin_centers) - 1
    median = float(bin_centers[median_idx])

    return mean, median, n


# ===============================
# 4. Vẽ 1 môn từ bảng bin (DataFrame binned)
# ===============================
def plot_subject_from_binned(
    binned: pd.DataFrame,
    subject: str,
    *,
    title: str | None = None,
    show: bool = True,
):
    """
    Vẽ phân phối điểm cho 1 môn từ bảng bin:
      - Trục X: bin (label khoảng)
      - Trục Y: số thí sinh
      - Mỗi năm = 1 đường
      - mean/median/n = ước lượng từ tâm bin
    """
    df_sub = binned[binned["mon"] == subject].copy()
    if df_sub.empty:
        print(f"⚠️ Không có dữ liệu cho môn: {subject}")
        return

    bins, centers, labels = _build_bins_and_labels(df_sub)
    if len(bins) == 0:
        print(f"⚠️ Không có bin cho môn: {subject}")
        return

    years = sorted(df_sub["nam_thi"].unique())

    plt.figure(figsize=(14, 6))

    for year in years:
        grp = df_sub[df_sub["nam_thi"] == year]
        if grp.empty:
            continue

        # map (start, end) -> count
        mapping = {
            (row.bin_start, row.bin_end): row.count
            for row in grp.itertuples(index=False)
        }

        counts = np.array([mapping.get((s, e), 0) for (s, e) in bins], dtype=float)

        mean, median, n = _approx_stats_from_binned(centers, counts)
        label = f"{year} (μ≈{mean:.2f}, med≈{median:.2f}, n={n})"

        plt.plot(centers, counts, marker="o", label=label)

    if title is None:
        title = f"Phân phối điểm môn {subject} theo năm (từ bảng bin)"

    plt.title(title)
    plt.xlabel("Khoảng điểm (bin)")
    plt.ylabel("Số thí sinh")

    plt.xticks(centers, labels, rotation=90, fontsize=8)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="Năm (ước lượng mean/median/n)", fontsize=9)
    plt.tight_layout()

    if show:
        plt.show()


# ===============================
# 5. Vẽ tất cả các môn
# ===============================
def plot_all_subjects_from_binned(
    binned: pd.DataFrame,
    subjects=SUBJECTS,
):
    """
    Vẽ lần lượt tất cả các môn trong subjects từ bảng bin.
    """
    for subj in subjects:
        print(f"Vẽ môn: {subj}")
        plot_subject_from_binned(binned, subj, show=True)


if __name__ == "__main__":
    # Demo nhỏ khi chạy trực tiếp file (tùy chọn)
    example_path = Path("diem_thi_binned_2019_2024.csv")
    if example_path.exists():
        binned_df = load_binned_scores(example_path)
        plot_subject_from_binned(binned_df, "Toán")
    else:
        print(
            f"Không tìm thấy {example_path}, "
            f"hãy tạo trước bằng export_binned_csv trong binned_scores.py."
        )
