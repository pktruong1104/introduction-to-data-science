import pandas as pd
import numpy as np
import json
import os 

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

def validate_and_process_scores(df, subject_cols, nguong_diem_liet):
    """Kiểm tra hợp lệ (0-10) và lọc theo ngưỡng điểm liệt."""
    
    df_clean = df.copy()
    count_before_liet = len(df_clean)

    # Kiểm tra tính hợp lệ (Data Validation 0-10)
    for col in subject_cols:
        df_clean[col] = df_clean[col].apply(lambda x: x if 0 <= x <= 10 else pd.NA)

    # Xử lý điểm liệt (Business Rule)
    actual_subject_cols_in_df = [col for col in subject_cols if col in df_clean.columns]
    
    # Lọc những thí sinh bị điểm <= ngưỡng liệt
    condition_liet = (df_clean[actual_subject_cols_in_df] <= nguong_diem_liet).any(axis=1)
    df_clean = df_clean[~condition_liet]
    
    stats = {}
    stats['Số lượng thí sinh bị điểm liệt'] = count_before_liet - len(df_clean)
    
    return df_clean, stats

def calculate_and_filter_tohop(df, config_path, nguong_diem_to_hop):
    """Tính điểm tổ hợp và lọc theo ngưỡng điểm sàn."""
    
    df_clean = df.copy()
    count_before_tohop = len(df_clean)
    
    # Load config tổ hợp
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            to_hop_dict = json.load(f)
    except Exception as e:
        print(f"Lỗi: Không thể đọc file config '{config_path}': {e}")
        return df_clean, {'Lỗi config': str(e)}

    to_hop_cols_calculated = []
    
    # Tính điểm tổ hợp
    for name, mon_thi in to_hop_dict.items():
        if all(mon in df_clean.columns for mon in mon_thi):
            to_hop_cols_calculated.append(name)
            all_subjects_present = df_clean[mon_thi].notna().all(axis=1) 
            df_clean[name] = df_clean[mon_thi].sum(axis=1)
            # Chỉ tính tổng cho những thí sinh có đủ điểm các môn tổ hợp
            df_clean.loc[~all_subjects_present, name] = pd.NA 

    if not to_hop_cols_calculated:
        return df_clean, {'Cảnh báo': 'Không có tổ hợp nào được tính.'} 

    # Lọc theo ngưỡng điểm sàn tổ hợp
    condition_tohop = (df_clean[to_hop_cols_calculated] >= nguong_diem_to_hop).any(axis=1)
    df_clean = df_clean[condition_tohop]
    
    stats = {}
    stats['Số lượng thí sinh tổ hợp không đạt yêu cầu'] = count_before_tohop - len(df_clean)
    
    return df_clean, stats

def preprocess_and_filter_data(df, config_path, nguong_diem_liet=1.0, nguong_diem_to_hop=15.0):
    """
    Hàm chính thực hiện toàn bộ quá trình xử lý và lọc dữ liệu.
    """
    
    # Khởi tạo Stats và DataFrame
    full_stats = {}
    full_stats['Số lượng trước khi lọc'] = len(df)
    original_cols = df.columns.tolist()
    
    # Làm sạch ban đầu (SBD, trùng lặp, kiểu dữ liệu)
    df_temp, subject_cols, stats_clean = clean_data_initial(df)
    full_stats.update(stats_clean)

    # Kiểm tra hợp lệ và Lọc điểm liệt
    df_temp, stats_liet = validate_and_process_scores(
        df_temp, 
        subject_cols, 
        nguong_diem_liet
    )
    full_stats.update(stats_liet)

    # Tính tổ hợp và Lọc điểm sàn
    df_final, stats_tohop = calculate_and_filter_tohop(
        df_temp, 
        config_path, 
        nguong_diem_to_hop
    )
    
    # Kiểm tra lỗi config
    if 'Lỗi config' in stats_tohop:
         full_stats.update(stats_tohop)
         return None, full_stats

    full_stats.update(stats_tohop)

    # Hoàn tất thống kê cuối cùng
    full_stats['Số lượng sau khi lọc'] = len(df_final)
    total_removed = full_stats['Số lượng trước khi lọc'] - full_stats['Số lượng sau khi lọc']
    
    if full_stats['Số lượng trước khi lọc'] > 0:
        full_stats['Phần % loại bỏ'] = round((total_removed / full_stats['Số lượng trước khi lọc']) * 100, 2)
    else:
        full_stats['Phần % loại bỏ'] = 0
        
    # Trả về các cột gốc (loại bỏ các cột tổ hợp tạm thời)
    final_cols_to_keep = [col for col in original_cols if col in df_final.columns]
    
    return df_final[final_cols_to_keep], full_stats

def process_single_year(year: int, config_file: str, DATA_DIR: os.PathLike, nguong_diem_liet: float, nguong_diem_to_hop: float):
    """
    Thực hiện đọc, làm sạch, lọc và lưu kết quả cho một năm cụ thể.

    Trả về dictionary stats của năm đó hoặc dictionary lỗi.
    """
    
    print(f"ĐANG XỬ LÝ NĂM: {year}")
    
    # Xác định file input/output (Giả định naming convention giống nhau)
    input_name = f"diem_thi_toan_quoc_{year}.csv"
    input_path = DATA_DIR / input_name
    output_name = f"diem_thi_{year}_new.csv"
    output_path = DATA_DIR / output_name

    try:
        # Đọc file
        print(f"Đang đọc: {input_name}")
        df_raw = pd.read_csv(input_path, low_memory=False)
        
        # Gọi hàm xử lý chính (preprocess_and_filter_data)
        df_filtered, year_stats = preprocess_and_filter_data(
            df_raw, 
            config_file, 
            nguong_diem_liet, 
            nguong_diem_to_hop
        )
        
        # Lưu kết quả
        if df_filtered is not None and not df_filtered.empty:
            df_filtered.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f" ĐÃ LƯU: {output_name} (Số lượng: {len(df_filtered)})")
        else:
            print(f" Cảnh báo: Không có dữ liệu nào còn lại cho năm {year} sau khi lọc.")
            
        # Hoàn tất stats
        year_stats['Năm'] = year
        return year_stats
        
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file input '{input_name}'. Bỏ qua năm {year}.")
        return {'Năm': year, 'Lỗi': f'Không tìm thấy file {input_name}'}
    
    except Exception as e:
        print(f"LỖI KHÔNG XÁC ĐỊNH với năm {year}: {e}")
        return {'Năm': year, 'Lỗi': str(e)}

def run_full_preprocessing(years_config: dict, DATA_DIR, nguong_diem_liet=1.0, nguong_diem_to_hop=15.0):
    """
    Quản lý vòng lặp xử lý dữ liệu qua nhiều năm.
    
    Args:
        years_config (dict): Dict {year: config_path}
        DATA_DIR (Path): Đường dẫn thư mục dữ liệu
        nguong_diem_liet (float): Ngưỡng điểm liệt để lọc
        nguong_diem_to_hop (float): Ngưỡng điểm sàn tổ hợp để lọc
        
    Returns:
        list: Danh sách các dictionary chứa số liệu thống kê của từng năm.
    """
    print(f"Bắt đầu xử lý {len(years_config)} năm...")
    print(f"Ngưỡng lọc hiện tại: Liệt <= {nguong_diem_liet}, Tổ hợp >= {nguong_diem_to_hop}")
    print("-" * 40)
    
    all_stats_list = []
    
    for year, config_file in years_config.items():
        stats_result = process_single_year(
            year, 
            config_file, 
            DATA_DIR,
            nguong_diem_liet, 
            nguong_diem_to_hop
        )
        all_stats_list.append(stats_result)
        print("-" * 40)
        
    print("--- TẤT CẢ QUY TRÌNH HOÀN TẤT ---")
    return all_stats_list

def display_stats_report(all_stats_list: list):
    """
    Chuyển list số liệu thống kê thành DataFrame, định dạng và hiển thị.
    """
    print("\nBẢNG TỔNG HỢP KẾT QUẢ LỌC DỮ LIỆU")

    if not all_stats_list or 'Lỗi' in all_stats_list[0].keys():
        print("Không có số liệu thống kê nào được thu thập hoặc có lỗi xảy ra.")
        return

    df_stats = pd.DataFrame(all_stats_list)
    
    columns_order = [
        'Năm', 
        'Số lượng trước khi lọc', 
        'Số lượng dữ liệu lỗi (SBD rỗng/trùng lặp)', 
        'Số lượng thí sinh bị điểm liệt', 
        'Số lượng thí sinh tổ hợp không đạt yêu cầu', 
        'Số lượng sau khi lọc',
        'Phần % loại bỏ',
        'Lỗi'
    ]
    
    # Lọc ra các cột thực sự tồn tại trong df_stats
    final_stat_cols = [col for col in columns_order if col in df_stats.columns]
    df_stats = df_stats[final_stat_cols]
    
    # Định dạng lại cột %
    if 'Phần % loại bỏ' in df_stats.columns:
        df_stats['Phần % loại bỏ'] = df_stats['Phần % loại bỏ'].map('{:,.2f}%'.format, na_action='ignore')

    # Hiển thị bảng 
    from IPython.display import display
    display(df_stats.set_index('Năm'))
