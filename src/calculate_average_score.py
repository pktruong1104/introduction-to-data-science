import pandas as pd
import json
import os


def calculate_average_score(nam_thi, file_input, file_output, file_tinh='ma_tinh.json'):
    """
    Hàm tính bảng xếp hạng điểm thi THPT theo tỉnh.
    
    Tham số:
    - nam_thi (int/str): Năm thi (ví dụ: 2024).
    - file_input (str): Đường dẫn đến file .csv dữ liệu điểm thi của năm đó.
    - file_tinh (str): Đường dẫn đến file .json dữ liệu mã số của các tỉnh.
    Trả về:
    - DataFrame bảng xếp hạng.
    """

    # 1. Đọc file JSON mã tỉnh
    try:
        with open(file_tinh,'r', encoding='utf-8') as f:
            raw_map = json.load(f)
            ma_tinh_map = {int(k): v for k, v in raw_map.items()}
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file'{file_tinh}'")
        return None
    
    # 2. Đọc file CSV điểm thi
    try:
        df = pd.read_csv(file_input)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file dữ liệu '{file_input}'")
        return None
    
    print(f"--- Đang xử lý dữ liệu năm {nam_thi} ---")

    # 3. Tính toán
    cols_score = [c for c in ['Toán', 'Văn', 'Ngoại ngữ', 'Lí', 'Hóa', 'Sinh', 'Sử', 'Địa', 'GDCD'] if c in df.columns]

    if not cols_score:
        print("Không có cột điểm nào.")
        return None
    
    df['TB_ThiSinh'] = df[cols_score].mean(axis=1)

    result = df.groupby('MA_TINH').agg(
        Diem_TB=('TB_ThiSinh', 'mean'),
        So_Thi_Sinh=('SBD', 'count')
    ).reset_index()

    # 4. Lấy tên tỉnh từ mã tỉnh
    result['Tỉnh/Thành phố'] = result['MA_TINH'].map(ma_tinh_map)

    # 5. Hoàn thiện
    result['Diem_TB'] = result['Diem_TB'].round(3)
    result = result.sort_values(by='Diem_TB', ascending=False)
    result.insert(0,'STT',range(1,len(result)+1))

    result = result.rename(columns={
        'Diem_TB': f'Điểm trung bình ({nam_thi})', 
        'So_Thi_Sinh': 'Tổng số thí sinh'
    })

    final_table = result[['STT', 'Tỉnh/Thành phố', f'Điểm trung bình ({nam_thi})', 'Tổng số thí sinh']]

    # 6. Lưu file csv kết quả
    output_filename = file_output
    final_table.to_csv(output_filename,index=False,encoding='utf-8-sig')

    print(f"Xong! Kết quả lưu tại: {output_filename}")
    return final_table
