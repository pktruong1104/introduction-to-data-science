import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplcursors

# Load tổ hợp từ JSON
def load_combinations(json_path="to_hop_cu.json"):
    with open(json_path, "r", encoding="utf8") as f:
        return json.load(f)

# Đọc và xử lý dữ liệu điểm thi
def load_score_files(data_folder="data", years=None):
    """
    years: list các năm cần đọc, ví dụ [2021, 2022, 2023]
           nếu None → đọc tất cả
    """
    all_files = []
    for f in os.listdir(data_folder):
        if f.startswith("diem_thi_") and f.endswith("_new.csv"):
            # Tách năm từ file: diem_thi_2023_new.csv → 2023
            year_str = f.replace("diem_thi_", "").replace("_new.csv", "")
            try:
                year = int(year_str)
            except:
                continue
            # Nếu không có lọc hoặc năm nằm trong danh sách → thêm file
            if (years is None) or (year in years):
                all_files.append(os.path.join(data_folder, f))
    if not all_files:
        print("⚠ Không có file nào khớp với danh sách năm:", years)
        return pd.DataFrame()
    # Đọc file
    df_all = []
    for file in all_files:
        print("Reading:", file)
        df = pd.read_csv(
            file,
            dtype={"MaMonNgoaiNgu": str, "SBD": str},
            low_memory=False
        )
        df_all.append(df)

    return pd.concat(df_all, ignore_index=True)

# Tính điểm tổ hợp cho từng thí sinh
def calc_combination_scores(df, combo_dict):
    """
    Trả về dict:
    pho_diem[khoi][nam] = Series điểm tổ hợp
    """
    pho_diem = {khoi: {} for khoi in combo_dict.keys()}

    for khoi, subjects in combo_dict.items():
        subjects_fixed = []

        for sub in subjects:
            if sub == "Ngoại ngữ":
                subjects_fixed.append("Ngoại ngữ")
            else:
                subjects_fixed.append(sub)
        for year, group in df.groupby("NĂM_THI"):
            # Chỉ giữ những thí sinh có đủ cả 3 môn
            group_valid = group.dropna(subset=subjects_fixed, how="any")
            # Nếu không ai đủ điểm → bỏ qua
            if group_valid.empty:
                pho_diem[khoi][year] = pd.Series(dtype=float)
                continue
            # Tính tổng điểm
            scores = group_valid[subjects_fixed].sum(axis=1)

            pho_diem[khoi][year] = scores

    return pho_diem

# Tìm điểm gần nhất để fill vào mốc 14–30
def find_nearest_score(target, available_scores, step=0.01, max_range=1.0):
    """
    Tìm điểm gần nhất target trong available_scores (±delta)
    """
    for delta in np.arange(step, max_range + step, step):
        low = round(target - delta, 2)
        high = round(target + delta, 2)
        if low in available_scores:
            return low
        if high in available_scores:
            return high
    return None

# Xây dựng phân phối số lượng thí sinh cho các mốc điểm 14–30.
def build_count_for_year(scores):
    """
    scores: Series điểm tổ hợp đã làm sạch
    Trả về dict {0: (count, real_used_score), ..., 30: (...)}
    """
    scores = scores.round(2)
    value_counts = scores.value_counts()
    available = set(value_counts.index)

    result = {}
    for target in range(14, 31):

        if target in available:
            result[target] = (int(value_counts[target]), float(target))
        else:
            nearest = find_nearest_score(target, available)
            if nearest is None:
                result[target] = (0, None)
            else:
                result[target] = (int(value_counts[nearest]), float(nearest))
    return result

# Build toàn bộ count_table
def build_all_counts(pho_diem):
    count_table = {}

    for khoi, year_dict in pho_diem.items():
        count_table[khoi] = {}

        for year, scores in year_dict.items():
            count_table[khoi][year] = build_count_for_year(scores)
    return count_table

# Vẽ biểu đồ
def plot_and_save_khoi(count_table, khoi, save_folder):
    os.makedirs(save_folder, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    xs = list(range(14, 31))   # 14–30
    lines = []                 # Lưu các đường để gắn cursor

    for year in sorted(count_table[khoi].keys()):
        ys = [count_table[khoi][year][d][0] for d in xs]

        line, = ax.plot(
            xs, ys,
            marker="o", markersize=5,
            linewidth=2,
            label=str(year)
        )
        lines.append(line)

    ax.set_title(f"So sánh phổ điểm khối {khoi} (2019-2024)", fontsize=16)
    ax.set_xlabel("Mốc điểm", fontsize=13)
    ax.set_ylabel("Số lượng thí sinh", fontsize=13)
    ax.grid(alpha=0.3)
    ax.legend()

    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])

    cursor = mplcursors.cursor(lines, hover=True)
    @cursor.connect("add")
    def on_add(sel):
        x, y = sel.target
        year = sel.artist.get_label()
        sel.annotation.set(
            text=f"Năm: {year}\nMốc: {int(x)}\nSố TS: {int(y)}",
            bgcolor="white"
        )

    plt.tight_layout()

    out_path = os.path.join(save_folder, f"khoi_{khoi}.png")
    plt.savefig(out_path, dpi=200)
    plt.close(fig)

    print(f"✔ Đã lưu biểu đồ: {out_path}")

# Main
if __name__ == "__main__":
    print("=== Đọc dữ liệu ===")
    YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
    df = load_score_files("data", years=YEARS)

    print("=== Gán tên môn ngoại ngữ ===")
    df["Ngoại ngữ"] = df["Ngoại ngữ"].astype(float)

    # Tải JSON tổ hợp
    combo = load_combinations("data\\to_hop_cu.json")

    print("=== Tính điểm tổ hợp ===")
    pho_diem = calc_combination_scores(df, combo)

    print("=== Tính số lượng theo mốc 14–30 ===")
    count_table = build_all_counts(pho_diem)

    print("=== Vẽ biểu đồ so sánh pho diem ===")
    KHOI = ["A00", "A01", "B00", "C00", "D01", "D07"]

    for khoi in KHOI:
        if khoi not in combo:
            print(f"[WARNING] Khối {khoi} không tồn tại trong danh sách tổ hợp!")
            continue
        plot_and_save_khoi(count_table, khoi, save_folder="data\\bieu_do_pho_diem")