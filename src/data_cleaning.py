import pandas as pd
import numpy as np
import json

def preprocess_and_filter_data(df, config_path):
    """
    Hàm này thực hiện toàn bộ quá trình:
    1. Làm sạch (SBD, types, duplicates)
    2. Validate (0-10)
    3. Lọc điểm liệt (<= 1.0)
    4. Lọc tổ hợp (>= 15)
    5. Tính và giữ lại điểm các tổ hợp
    
    Args:
        df (pd.DataFrame): DataFrame thô.
        config_path (str or Path): Đường dẫn đến file to_hop.json.

    Returns:
        pd.DataFrame: DataFrame đã được xử lý.
    """
    
    print(f"Bắt đầu xử lý. Số lượng ban đầu: {len(df)}")
    
    # Tạo bản sao
    df_clean = df.copy()

    # === BƯỚC 1: Xử lý giá trị thiếu (SBD) ===
    df_clean.dropna(subset=['SBD'], inplace=True)
    print(f"Sau khi loại bỏ SBD rỗng: {len(df_clean)}")

    # === BƯỚC 2: Xử lý trùng lặp (SBD) ===
    df_clean.drop_duplicates(subset=['SBD'], keep='first', inplace=True)
    print(f"Sau khi loại bỏ SBD trùng lặp: {len(df_clean)}")

    # === BƯỚC 3: Chuẩn hóa kiểu dữ liệu ===
    df_clean['SBD'] = df_clean['SBD'].astype(str)
    
    all_cols = df_clean.columns.tolist()
    subject_cols = [col for col in all_cols if col not in ['MA_TINH', 'SBD']]
    
    for col in subject_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
    subject_cols = [col for col in subject_cols if col in df_clean.columns]

    # === BƯỚC 4: Kiểm tra tính hợp lệ (Data Validation) ===
    for col in subject_cols:
        df_clean[col] = df_clean[col].apply(lambda x: x if 0 <= x <= 10 else pd.NA)

    # === BƯỚC 5: Xử lý điểm liệt (Business Rule) ===
    actual_subject_cols_in_df = [col for col in subject_cols if col in df_clean.columns]
    condition_liet = (df_clean[actual_subject_cols_in_df] <= 1.0).any(axis=1)
    df_clean = df_clean[~condition_liet]
    print(f"Sau khi loại bỏ điểm liệt (<= 1.0): {len(df_clean)}")

    # === BƯỚC 6 & 7: Tính và Lọc theo Tổ hợp >= 15 ===
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            to_hop_dict = json.load(f)
        print(f"Đã tải thành công {len(to_hop_dict)} tổ hợp từ '{config_path}'")
    except Exception as e:
        print(f"Lỗi: Không thể đọc file config '{config_path}': {e}")
        return None
    
    to_hop_cols_calculated = []
    print("Đang tính toán điểm các tổ hợp...")
    
    for name, mon_thi in to_hop_dict.items():
        if all(mon in df_clean.columns for mon in mon_thi):
            to_hop_cols_calculated.append(name)
            all_subjects_present = df_clean[mon_thi].notna().all(axis=1) 
            df_clean[name] = df_clean[mon_thi].sum(axis=1)
            df_clean.loc[~all_subjects_present, name] = pd.NA 

    if not to_hop_cols_calculated:
        print("Cảnh báo: Không có tổ hợp nào được tính.")
        return df_clean 

    condition_15 = (df_clean[to_hop_cols_calculated] >= 15).any(axis=1)
    df_clean = df_clean[condition_15]
    print(f"Sau khi lọc theo tổ hợp >= 15đ: {len(df_clean)}")
    
    # === BƯỚC 8: Hoàn tất ===
    original_cols = df.columns.tolist()
    final_cols = original_cols + to_hop_cols_calculated
    final_cols_unique = []
    for col in final_cols:
        if col in df_clean.columns and col not in final_cols_unique:
            final_cols_unique.append(col)
    
    print("Hoàn tất xử lý.")
    return df_clean[final_cols_unique]
