import pandas as pd
import numpy as np
import json
import os 

def preprocess_and_filter_data(df, config_path):
    """
    Hàm này thực hiện toàn bộ quá trình:
    1. Làm sạch (SBD, types, duplicates)
    2. Validate (0-10)
    3. Lọc điểm liệt (<= 1.0)
    4. Lọc tổ hợp (>= 15)
    5. Trả về DataFrame đã lọc VÀ 1 dictionary chứa số liệu thống kê (stats)
    
    Args:
        df (pd.DataFrame): DataFrame thô.
        config_path (str or Path): Đường dẫn đến file to_hop.json.

    Returns:
        (pd.DataFrame, dict): (DataFrame đã xử lý, Dictionary số liệu)
    """
    
    # === BƯỚC 0: Khởi tạo Stats ===
    stats = {}
    stats['Số lượng trước khi lọc'] = len(df)
    
    # Lấy danh sách các cột gốc TRƯỚC KHI thêm cột tổ hợp
    original_cols = df.columns.tolist()
    
    # Tạo bản sao
    df_clean = df.copy()

    # === BƯỚC 1: Xử lý giá trị thiếu (SBD) ===
    df_clean.dropna(subset=['SBD'], inplace=True)
    count_after_dropna = len(df_clean)

    # === BƯỚC 2: Xử lý trùng lặp (SBD) ===
    df_clean.drop_duplicates(subset=['SBD'], keep='first', inplace=True)
    count_after_dropdups = len(df_clean)
    
    stats['Số lượng dữ liệu lỗi (SBD rỗng/trùng lặp)'] = stats['Số lượng trước khi lọc'] - count_after_dropdups

    # === BƯỚC 3: Chuẩn hóa kiểu dữ liệu ===
    df_clean['SBD'] = df_clean['SBD'].astype(str)
    
    all_cols = df_clean.columns.tolist()
    subject_cols = [col for col in all_cols if col not in ['NĂM_THI', 'MA_TINH', 'SBD', 'MaMonNgoaiNgu']]
    
    for col in subject_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
    subject_cols = [col for col in subject_cols if col in df_clean.columns]

    # === BƯỚC 4: Kiểm tra tính hợp lệ (Data Validation) ===
    # (Bước này chỉ gán NaN, không lọc)
    for col in subject_cols:
        df_clean[col] = df_clean[col].apply(lambda x: x if 0 <= x <= 10 else pd.NA)

    # === BƯỚC 5: Xử lý điểm liệt (Business Rule) ===
    count_before_liet = len(df_clean) # Số lượng trước khi lọc liệt
    actual_subject_cols_in_df = [col for col in subject_cols if col in df_clean.columns]
    condition_liet = (df_clean[actual_subject_cols_in_df] <= 1.0).any(axis=1)
    df_clean = df_clean[~condition_liet]
    count_after_liet = len(df_clean)
    
    stats['Số lượng thí sinh bị điểm liệt'] = count_before_liet - count_after_liet
    # print(f"Sau khi lọc điểm liệt: {count_after_liet}")

    # === BƯỚC 6 & 7: Tính và Lọc theo Tổ hợp >= 15 ===
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            to_hop_dict = json.load(f)
        # print(f"Đã tải {len(to_hop_dict)} tổ hợp từ '{os.path.basename(str(config_path))}'")
    except Exception as e:
        print(f"Lỗi: Không thể đọc file config '{config_path}': {e}")
        return None, stats
    
    to_hop_cols_calculated = []
    
    for name, mon_thi in to_hop_dict.items():
        if all(mon in df_clean.columns for mon in mon_thi):
            to_hop_cols_calculated.append(name)
            all_subjects_present = df_clean[mon_thi].notna().all(axis=1) 
            df_clean[name] = df_clean[mon_thi].sum(axis=1)
            df_clean.loc[~all_subjects_present, name] = pd.NA 

    if not to_hop_cols_calculated:
        print("Cảnh báo: Không có tổ hợp nào được tính.")
        return df_clean, stats 

    count_before_tohop = len(df_clean) # Số lượng trước khi lọc tổ hợp
    condition_15 = (df_clean[to_hop_cols_calculated] >= 15).any(axis=1)
    df_clean = df_clean[condition_15]
    count_after_tohop = len(df_clean)
    
    stats['Số lượng thí sinh tổ hợp không đạt yêu cầu (>=15)'] = count_before_tohop - count_after_tohop
    # print(f"Sau khi lọc theo tổ hợp >= 15đ: {count_after_tohop}")
    
    # === BƯỚC 8: Hoàn tất ===
    
    stats['Số lượng sau khi lọc'] = count_after_tohop
    total_removed = stats['Số lượng trước khi lọc'] - stats['Số lượng sau khi lọc']
    
    # Tính phần trăm
    if stats['Số lượng trước khi lọc'] > 0:
        stats['Phần % loại bỏ'] = (total_removed / stats['Số lượng trước khi lọc']) * 100
    else:
        stats['Phần % loại bỏ'] = 0
        
    final_cols_to_keep = [col for col in original_cols if col in df_clean.columns]
    
    # print("Hoàn tất xử lý. (Đã loại bỏ các cột tổ hợp tạm thời).")
    
    return df_clean[final_cols_to_keep], stats
