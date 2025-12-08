import pandas as pd
import matplotlib.pyplot as plt
import glob
import numpy as np
import os

# Đọc toàn bộ file summary 2019–2024
VALID_YEARS =  ["2019", "2020", "2021", "2022", "2023", "2024"]
DATA_FOLDER = "data"   # Thư mục chứa file summary
SAVE_FOLDER = os.path.join(DATA_FOLDER, "bieu_do_pho_diem")

os.makedirs(SAVE_FOLDER, exist_ok=True)

all_files = glob.glob(os.path.join(DATA_FOLDER, "*_summary.csv"))
if len(all_files) == 0:
    raise FileNotFoundError("Không tìm thấy file *_summary.csv trong thư mục 'data/'")

dfs = []
for file in all_files:
    year = os.path.basename(file).split("_")[0]
    if year not in VALID_YEARS:
        continue

    print(f"Đang đọc: {file}")
    df = pd.read_csv(file)
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# Các khối thi được chọn
KHOI = ["A00", "B00", "C00", "D01", "D07"]

df_all = df_all[df_all["KHOI_THI"].isin(KHOI)]
if df_all.empty:
    raise ValueError("Không có dữ liệu sau khi lọc các khối A00, B00, C00, D00, D01, D07")

df_all["NĂM_THI"] = df_all["NĂM_THI"].astype(int)
YEARS = sorted(df_all["NĂM_THI"].unique())
print("Danh sách năm tìm thấy:", YEARS)

# Vẽ biểu đồ đường phổ điểm theo từng khối
def plot_pho_diem(df, khoi):
    plt.figure(figsize=(14, 7))

    # 1. Tạo danh sách chuẩn: Đảm bảo có đủ các mốc từ 0 đến 30
    valid_mocs = [x * 1.0 for x in range(15, 31)] 
    df_template = pd.DataFrame({"MOC_DIEM": valid_mocs})

    for year in YEARS:
        df_year = df[df["NĂM_THI"] == year]

        # Tính toán số lượng thí sinh
        df_agg = (
            df_year[df_year["MOC_DIEM"].isin(valid_mocs)]
            .groupby("MOC_DIEM")["SO_THI_SINH"].sum()
            .reset_index()
        )
        
        # LẤP ĐẦY DỮ LIỆU (Bởi vì sẽ có những năm không có thì sinh đạt tổ hợp 30 điểm)
        # Merge dữ liệu tính được vào khung chuẩn (df_template). giữ lại tất cả mốc từ 0-30
        # .fillna(0): Mốc nào không có người thi (ví dụ 30 điểm) sẽ điền là 0
        df_plot = pd.merge(df_template, df_agg, on="MOC_DIEM", how="left").fillna(0)
        
        # Vẽ biểu đồ
        plt.plot(
            df_plot["MOC_DIEM"],
            df_plot["SO_THI_SINH"],
            linewidth=2,
            marker="o",
            markersize=5,
            markeredgewidth=0.5,
            label=str(year)
        )

    # --- CẤU HÌNH TRỤC X ---
    start_point = 15
    end_point = 30
    
    # Ép hiển thị đủ số từ 15 đến 30 (cách nhau 1 đơn vị)
    plt.xticks(np.arange(start_point, end_point + 1, 1), fontsize=11)
    
    # Nới rộng trục ra một chút (+0.5) để điểm 30 không bị cắt mất
    plt.xlim(start_point - 0.5, end_point + 0.5)
    # -----------------------

    plt.title(f"So sánh phổ điểm khối {khoi} (2019–2024)", fontsize=16, fontweight='bold')
    plt.xlabel(f"Điểm khối {khoi}", fontsize=12)
    plt.ylabel("Số thí sinh", fontsize=12)
    
    plt.grid(True, which='both', linestyle="--", alpha=0.5)
    plt.legend(title="Năm thi")
    plt.tight_layout()

    save_path = os.path.join(SAVE_FOLDER, f"bieu_do_pho_diem_khoi_{khoi}.png")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f" → Đã lưu: {save_path}")

    # plt.show()

# Vẽ tất cả các khối
for khoi in KHOI:
    print(f"\n=== Đang vẽ biểu đồ khối {khoi} ===")
    df_khoi = df_all[df_all["KHOI_THI"] == khoi]

    if df_khoi.empty:
        print(f"Không có dữ liệu cho khối {khoi}")
        continue
    plot_pho_diem(df_khoi, khoi)