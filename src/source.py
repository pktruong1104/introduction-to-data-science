import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
import json 
import geopandas as gpd 
from pathlib import Path

# ============================ HÀM ĐỒNG BỘ ID VỚI MÃ TỈNH TRA CỨU VIETNAMNET =============================# 
def standarlize_geojson_id(geojson_path: Path, csv_path: Path): 
    gdf = gpd.read_file(geojson_path)
    df_csv = pd.read_csv(csv_path)

    df_new = df_csv[['TEN_TINH', 'MA_TINH']]

    # lấy cột trong json 
    TEN_COL_JSON = 'name'
    TEN_COL_CSV = 'TEN_TINH'

    gdf_merged = gdf.merge(
        df_new,
        left_on = TEN_COL_JSON, 
        right_on = TEN_COL_CSV,
        how='left'
    )

    gdf_merged['id'] = gdf_merged['MA_TINH'].combine_first(gdf_merged['id'])
    gdf_final = gdf_merged.drop(columns=['TEN_TINH'])
    gdf_final['MA_TINH'] = gdf_final['MA_TINH'].fillna(0).astype(int)

    gdf_final = gdf_final.set_index('id')
    gdf_final.index.name = 'id'

    gdf_final.to_file("vn_new.json", driver="GeoJSON")
    print("Đã lưu GeoJSON mới với ID đã cập nhật thành công!")

# ============================================ XỬ LÍ LẠI DỮ LIỆU THÍ SINH ===================================
def clean_data_initial(df):
    """Làm sạch ban đầu: Xử lý thiếu/trùng lặp SBD và chuẩn hóa kiểu dữ liệu."""
    df_clean = df.copy()
    initial_count = len(df_clean)

    # Xử lý giá trị thiếu (SBD)
    df_clean.dropna(subset=['SBD'], inplace=True)
    
    # Xử lý trùng lặp (SBD)
    df_clean.drop_duplicates(subset=['SBD'], keep='first', inplace=True)
    
    # Chuẩn hóa kiểu dữ liệu
    df_clean['SBD'] = df_clean['SBD'].astype(str)
    
    all_cols = df_clean.columns.tolist()
    subject_cols = [col for col in all_cols if col not in ['NĂM_THI', 'MA_TINH', 'SBD', 'MaMonNgoaiNgu']]
    
    # Chuyển điểm số sang kiểu số thực
    for col in subject_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            
    # Tính stats cơ bản
    stats = {}
    stats['Số lượng dữ liệu lỗi (SBD rỗng/trùng lặp)'] = initial_count - len(df_clean)
    
    return df_clean, subject_cols, stats

# ====================================== TÍNH TOÁN SỐ LƯỢNG & TỶ LỆ ĐỂ VẼ =================================
def calculate_heatmap_stats_by_tinh(df_raw, config_path, nguong_diem_liet=1.0, nguong_diem_to_hop=15.0):
    """
    Tính toán số lượng/tỷ lệ thí sinh theo 2 trường hợp:
    - TH1: Thí sinh liệt (có điểm môn bất kỳ < ngưỡng)
    - TH2: Thí sinh liệt HOẶC không đạt ngưỡng tổ hợp
    """
    df_temp = df_raw.copy()
    
    # 1. Làm sạch ban đầu
    df_temp, subject_cols, _ = clean_data_initial(df_temp)
    
    # 2. Xử lý điểm liệt
    df_liet = df_temp.copy()
    
    # Chuẩn hóa điểm (chỉ giữ điểm hợp lệ 0-10)
    for col in subject_cols:
        df_liet[col] = df_liet[col].apply(lambda x: x if 0 <= x <= 10 else pd.NA)
    
    # Đánh dấu thí sinh có điểm liệt
    actual_subject_cols = [col for col in subject_cols if col in df_liet.columns]
    condition_liet = (df_liet[actual_subject_cols] <= nguong_diem_liet).any(axis=1)
    df_liet['is_liet'] = condition_liet
    
    # 3. Xử lý ngưỡng tổ hợp
    df_tohop = df_liet.copy()
    
    to_hop_cols_calculated = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            to_hop_dict = json.load(f)
    except Exception as e:
        print(f"Cảnh báo: Lỗi config tổ hợp ({e}). Chỉ tính thống kê điểm liệt.")
        to_hop_dict = {}
    
    # Tính điểm các tổ hợp
    for name, mon_thi in to_hop_dict.items():
        if all(mon in df_tohop.columns for mon in mon_thi):
            to_hop_cols_calculated.append(name)
            all_subjects_present = df_tohop[mon_thi].notna().all(axis=1)
            df_tohop[name] = df_tohop[mon_thi].sum(axis=1)
            df_tohop.loc[~all_subjects_present, name] = pd.NA
    
    # Đánh dấu thí sinh không đạt ngưỡng tổ hợp
    if to_hop_cols_calculated:
        condition_dat_tohop = (df_tohop[to_hop_cols_calculated] >= nguong_diem_to_hop).any(axis=1)
        df_tohop['is_khong_dat_tohop'] = ~condition_dat_tohop.fillna(True)
    else:
        df_tohop['is_khong_dat_tohop'] = False
    
    # 4. Kết hợp 2 điều kiện cho TH2
    df_tohop['is_liet_hoac_khong_dat_tohop'] = df_tohop['is_liet'] | df_tohop['is_khong_dat_tohop']
    
    # 5. Thống kê theo tỉnh
    df_total_by_tinh = df_temp.groupby('MA_TINH').size().reset_index(name='Tong_thi_sinh_hop_le')
    
    # Thống kê TH1: Chỉ điểm liệt
    df_liet_count_th1 = df_liet[df_liet['is_liet'] == True]\
        .groupby('MA_TINH').size().reset_index(name='So_luong_liet')
    
    # Thống kê TH2: Liệt HOẶC không đạt tổ hợp
    df_liet_count_th2 = df_tohop[df_tohop['is_liet_hoac_khong_dat_tohop'] == True]\
        .groupby('MA_TINH').size().reset_index(name='So_luong_liet_ca_2')
    
    # 6. Gộp vào df_total_by_tinh
    # Merge TH1
    df_total_by_tinh = pd.merge(df_total_by_tinh, df_liet_count_th1, on='MA_TINH', how='left')
    
    # Merge TH2
    df_total_by_tinh = pd.merge(df_total_by_tinh, df_liet_count_th2, on='MA_TINH', how='left')
    
    # 7. Điền giá trị 0 và tính tỷ lệ
    for col in ['So_luong_liet', 'So_luong_liet_ca_2']:
        if col in df_total_by_tinh.columns:
            df_total_by_tinh[col] = df_total_by_tinh[col].fillna(0).astype(int)
    
    # Tính tỷ lệ phần trăm
    if 'So_luong_liet' in df_total_by_tinh.columns:
        df_total_by_tinh['Ty_le_liet_TH1'] = (df_total_by_tinh['So_luong_liet'] / df_total_by_tinh['Tong_thi_sinh_hop_le']) * 100
    
    if 'So_luong_liet_ca_2' in df_total_by_tinh.columns:
        df_total_by_tinh['Ty_le_liet_TH2'] = (df_total_by_tinh['So_luong_liet_ca_2'] / df_total_by_tinh['Tong_thi_sinh_hop_le']) * 100
    
    # Làm tròn tỷ lệ
    for col in ['Ty_le_liet_TH1', 'Ty_le_liet_TH2']:
        if col in df_total_by_tinh.columns:
            df_total_by_tinh[col] = df_total_by_tinh[col].round(2)
    
    return df_total_by_tinh

# ========================================= VẼ BẢN ĐỒ NHIỆT ====================================
def draw_dual_heatmap(gdf_year: gpd.GeoDataFrame, year: int, output_dir: Path):
    """
    Vẽ hai bản đồ nhiệt (Số lượng và Tỷ lệ) cạnh nhau cho dữ liệu điểm liệt.
    """
    
    # Kiểm tra các cột cần thiết có tồn tại không
    required_cols = ['So_luong_liet_ca_2', 'Ty_le_liet_TH2']
    if not all(col in gdf_year.columns for col in required_cols):
        print("LỖI: GeoDataFrame thiếu các cột thống kê cần thiết (So_luong_liet hoặc Ty_le_liet).")
        return

    # Tạo hình (figure) và 2 ô đồ thị (axes) cạnh nhau (1 hàng, 2 cột)
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(22, 11)) 
    
    # ----------------------------------------------------
    # 1. BẢN ĐỒ THỂ HIỆN SỐ LƯỢNG (Absolute Number)
    # ----------------------------------------------------
    ax1 = axes[0] 
    gdf_year.plot(
        column='So_luong_liet_ca_2',  # Dữ liệu Số lượng tuyệt đối
        cmap='Reds',             # Dải màu Đỏ cho thấy quy mô
        linewidth=0.8,
        edgecolor='0.8',
        legend=True,
        legend_kwds={'label': "Số lượng thí sinh điểm liệt", 'orientation': "horizontal"},
        ax=ax1,                  # Vẽ trên ô đồ thị thứ nhất
        missing_kwds={'color': 'lightgrey'} 
    )
    ax1.set_title(f'Năm {year}: Số Lượng Thí Sinh Bị Điểm Liệt', fontsize=16)
    ax1.axis('off') # Ẩn trục tọa độ
    
    # ----------------------------------------------------
    # 2. BẢN ĐỒ THỂ HIỆN TỶ LỆ (Rate/Percentage)
    # ----------------------------------------------------
    ax2 = axes[1] 
    gdf_year.plot(
        column='Ty_le_liet_TH2',     # Dữ liệu Tỷ lệ phần trăm
        cmap='OrRd',             # Dải màu Cam-Đỏ cho thấy cường độ/chất lượng
        linewidth=0.8,
        edgecolor='0.8',
        legend=True,
        legend_kwds={'label': "Tỷ lệ thí sinh điểm liệt (%)", 'orientation': "horizontal"},
        ax=ax2,                  # Vẽ trên ô đồ thị thứ hai
        missing_kwds={'color': 'lightgrey'}
    )
    ax2.set_title(f'Năm {year}: Tỷ Lệ Thí Sinh Bị Điểm Liệt (%)', fontsize=16)
    ax2.axis('off') 
    
    plt.suptitle(f'Bản đồ Nhiệt So Sánh Điểm Liệt Kỳ Thi THPT Quốc Gia Năm {year}', fontsize=20, y=0.95) 

    # Lưu hình ảnh
    output_file = output_dir / f"heatmap_dual_{year}.png"
    plt.savefig(output_file, dpi=300)
    plt.close(fig)
    print(f"ĐÃ LƯU BẢN ĐỒ KÉP: {output_file.name}")

# ======================================== CHẠY TỪNG NĂM ====================================
def run_single_year_analysis(data_path, config_path, liet_nguong, tohop_nguong):
    """Đọc dữ liệu, tính toán thống kê và trả về DataFrame kết quả."""
    print(f"Bắt đầu đọc file: {data_path.name}")
    
    try:
        # 1. Đọc file CSV
        df_raw = pd.read_csv(data_path, low_memory=False)

        # 2. Tính toán thống kê theo tỉnh
        # (Sử dụng hàm calculate_heatmap_stats_by_tinh đã được cải tiến)
        df_temp, subject_cols, _ = clean_data_initial(df_raw.copy()) 
        df_stats_by_tinh = calculate_heatmap_stats_by_tinh(
            df_raw, # Truyền df_raw hoặc df_temp tùy thuộc vào cách bạn thiết kế hàm
            config_path, 
            liet_nguong, 
            tohop_nguong
        )
        
        print("Đã tính toán thống kê thành công.")
        return df_stats_by_tinh
        
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file tại đường dẫn: {data_path}")
        return None
    except Exception as e:
        print(f"LỖI XỬ LÝ DỮ LIỆU: {e}")
        return None

# ===================================== THỐNG KÊ VÀ VẼ =========================================
def run_full_analysis_and_draw(year: int, data_file_path: Path, config_file_path: Path, 
                               geojson_path: Path, output_dir: Path, 
                               liet_nguong: float, tohop_nguong: float):
    """
    Thực hiện toàn bộ quy trình: Đọc dữ liệu, tính toán thống kê, gộp vào bản đồ, 
    và vẽ bản đồ nhiệt kép cho một năm.
    """
    
    # 1. TẢI DỮ LIỆU ĐIỂM THI VÀ TÍNH TOÁN THỐNG KÊ
    df_stats_by_tinh = run_single_year_analysis(
        data_file_path, 
        config_file_path, 
        liet_nguong, 
        tohop_nguong
    )

    if df_stats_by_tinh is None:
        return # Dừng nếu có lỗi trong quá trình xử lý dữ liệu

    # 2. TẢI BẢN ĐỒ NỀN
    try:
        gdf_base = gpd.read_file(geojson_path)
    except Exception as e:
        print(f"LỖI: Không thể đọc file GeoJSON {geojson_path}. {e}")
        return

    # 3. GỘP DỮ LIỆU THỐNG KÊ VÀO BẢN ĐỒ
    
    # Đảm bảo cột MA_TINH trong thống kê cũng là int
    df_stats_by_tinh['MA_TINH'] = df_stats_by_tinh['MA_TINH'].astype(int)
    
    # Gộp (Merge)
    gdf_year = gdf_base.merge(
        df_stats_by_tinh, 
        left_on='MA_TINH', 
        right_on='MA_TINH', 
        how='left'
    )
    
    # Chuẩn hóa dữ liệu sau gộp (Điền 0 cho các tỉnh thiếu dữ liệu)
    # Vẽ cho trường hợp 2 
    gdf_year['So_luong_liet_ca_2'] = gdf_year['So_luong_liet_ca_2'].fillna(0)
    gdf_year['Ty_le_liet_TH2'] = gdf_year['Ty_le_liet_TH2'].fillna(0)
    # (Bạn có thể thêm các cột tổ hợp nếu muốn vẽ bản đồ tổ hợp)
    
    print("Đã gộp dữ liệu thống kê vào bản đồ thành công.")

    # 4. VẼ BẢN ĐỒ NHIỆT KÉP (Gọi hàm vẽ đã định nghĩa)
    draw_dual_heatmap(gdf_year, year, output_dir)
    
    print("QUY TRÌNH VẼ BẢN ĐỒ NHIỆT HOÀN TẤT.")

# ===================================== CHẠY NHIỀU NĂM ==========================================
def run_multi_year_analysis(
    years: list[int],
    data_dir: Path,
    config_file_path: Path,
    geojson_path: Path,
    output_root: Path,
    liet_nguong: float = 1.0,
    tohop_nguong: float = 15.0
):
    for year in years:
        print(f"\n=== BẮT ĐẦU PHÂN TÍCH NĂM {year} ===")

        data_file = data_dir / f"{year}.csv"
        output_dir = output_root / str(year)
        output_dir.mkdir(parents=True, exist_ok=True)

        run_full_analysis_and_draw(
            year=year,
            data_file_path=data_file,
            config_file_path=config_file_path,
            geojson_path=geojson_path,
            output_dir=output_dir,
            liet_nguong=liet_nguong,
            tohop_nguong=tohop_nguong
        )

def main():
    
    YEARS = [2019, 2020, 2021, 2022, 2023,2024]  

    DATA_DIR = Path("../data")           
    
    OUTPUT_DIR = Path("../output")

    
    OUTPUT_DIR.mkdir(exist_ok=True)

    CONFIG_FILE = DATA_DIR / "to_hop.json"
    GEOJSON_FILE = DATA_DIR / "vn_new.json"
    NGUONG_LIET = 1.0
    NGUONG_TO_HOP = 15.0

    GEOJSON_OLD = DATA_DIR / "vn.json"
    PROVINCE_CSV = DATA_DIR / "province.csv"
    # xử lí json cũ 
    standarlize_geojson_id(GEOJSON_OLD, PROVINCE_CSV)



    for year in YEARS:
        print(f"\n========== NĂM {year} ==========")

        data_file = DATA_DIR / f"diem_thi_toan_quoc_{year}.csv"
        year_output_dir = OUTPUT_DIR / str(year)
        year_output_dir.mkdir(parents=True, exist_ok=True)

        if not data_file.exists():
            print(f"BỎ QUA: Không tìm thấy file {data_file.name}")
            continue

        run_full_analysis_and_draw(
            year=year,
            data_file_path=data_file,
            config_file_path=CONFIG_FILE,
            geojson_path=GEOJSON_FILE,
            output_dir=year_output_dir,
            liet_nguong=NGUONG_LIET,

            tohop_nguong=NGUONG_TO_HOP
        )

    print("\n HOÀN TẤT PHÂN TÍCH TẤT CẢ CÁC NĂM")

if __name__ == "__main__":
    main()