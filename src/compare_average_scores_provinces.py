import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns


def calculate_average_scores_by_subject(nam_thi, file_input, file_output, file_tinh='ma_tinh.json'):
    """
    Hàm tính điểm trung bình TỪNG MÔN thi THPT theo tỉnh.
    
    Tham số:
    - nam_thi (int/str): Năm thi (ví dụ: 2024).
    - file_input (str): Đường dẫn đến file .csv dữ liệu điểm thi của năm đó.
    - file_tinh (str): Đường dẫn đến file .json dữ liệu mã số của các tỉnh.
    Trả về:
    - DataFrame điểm trung bình từng môn (Tên cột KHÔNG có năm).
    """
    nam_thi = str(nam_thi) # Đảm bảo năm là chuỗi để sử dụng trong tên cột
    
    # 1. Đọc file JSON mã tỉnh
    try:
        with open(file_tinh,'r', encoding='utf-8') as f:
            raw_map = json.load(f)
            ma_tinh_map = {int(k): v for k, v in raw_map.items()}
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file'{file_tinh}'")
        return None
    except Exception as e:
        print(f"Lỗi đọc file JSON: {e}")
        return None
    
    # 2. Đọc file CSV điểm thi
    try:
        df = pd.read_csv(file_input)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file dữ liệu '{file_input}'")
        return None
    
    print(f"--- Đang xử lý dữ liệu TỪNG MÔN năm {nam_thi} ---")

    # 3. Tính toán Điểm Trung bình Từng Môn
    
    # Danh sách các cột điểm cần tính trung bình
    all_subjects = ['Toán', 'Văn', 'Ngoại ngữ', 'Lí', 'Hóa', 'Sinh', 'Sử', 'Địa', 'GDCD']
    cols_score = [c for c in all_subjects if c in df.columns]

    if not cols_score:
        print("Không có cột điểm môn học nào.")
        return None
    
    # Tạo dictionary cho hàm agg
    agg_dict = {col: 'mean' for col in cols_score}
    agg_dict['SBD'] = 'count'

    # Thực hiện Groupby theo MA_TINH và tính trung bình cho tất cả các môn
    result = df.groupby('MA_TINH').agg(agg_dict).reset_index()
    
    # Đổi tên cột đếm SBD
    result = result.rename(columns={'SBD': 'Tổng số thí sinh'})


    # 4. Lấy tên tỉnh từ mã tỉnh
    result['Tỉnh/Thành phố'] = result['MA_TINH'].map(ma_tinh_map)
    # Loại bỏ MA_TINH
    result = result.drop(columns=['MA_TINH'])

    # 5. Hoàn thiện và Định dạng
    
    cols_score_no_year = []
    df_to_save = result.copy()
    
    # Lặp qua từng môn để làm tròn và đổi tên
    for col in cols_score:
        result[col] = result[col].round(3)
        df_to_save[col] = df_to_save[col].round(3)
        
        # Tên cột CÓ NĂM (Dùng để LƯU CSV)
        col_name_with_year = f'Điểm TB {col} ({nam_thi})'
        
        # Tên cột KHÔNG CÓ NĂM (Dùng cho DataFrame TRẢ VỀ)
        col_name_no_year = f'Điểm TB {col}'
        
        # Đổi tên trong DataFrame TRẢ VỀ (result)
        result = result.rename(columns={col: col_name_no_year})
        
        # Đổi tên trong DataFrame LƯU CSV (df_to_save)
        df_to_save = df_to_save.rename(columns={col: col_name_with_year})
        
        cols_score_no_year.append(col_name_no_year)

    # 6. Sắp xếp lại thứ tự cột
    
    # Thêm cột STT vào DataFrame TRẢ VỀ
    result['STT'] = result['Tỉnh/Thành phố'].rank(method='first').astype(int)
    final_cols = ['STT', 'Tỉnh/Thành phố', 'Tổng số thí sinh'] + cols_score_no_year
    final_table = result[final_cols].sort_values(by='Tỉnh/Thành phố').reset_index(drop=True)
    final_table['STT'] = range(1, len(final_table) + 1) # Đánh STT lại theo thứ tự tỉnh

    # Thêm cột STT vào DataFrame LƯU CSV
    df_to_save['STT'] = df_to_save['Tỉnh/Thành phố'].rank(method='first').astype(int)
    save_cols = ['STT', 'Tỉnh/Thành phố', 'Tổng số thí sinh'] + [f'Điểm TB {col} ({nam_thi})' for col in cols_score]
    df_to_save = df_to_save[save_cols].sort_values(by='Tỉnh/Thành phố').reset_index(drop=True)
    df_to_save['STT'] = range(1, len(df_to_save) + 1)
    
    # 7. Lưu file csv kết quả (CÓ NĂM TRONG TÊN CỘT)
    output_filename = file_output
    final_table.to_csv(output_filename, index=False, encoding='utf-8-sig')

    print(f"Xong! Kết quả điểm trung bình từng môn lưu tại: {output_filename}")
    
    # Trả về DataFrame KHÔNG CÓ NĂM trong tên cột
    return final_table

def visualize_subject_ranking(df_input, subject, nam_thi, output_dir):
    """
    Tạo biểu đồ thanh ngang xếp hạng điểm trung bình cho một môn học cụ thể.
    Sử dụng bảng màu đa dạng (tab10) cho mỗi tỉnh, lưu vào thư mục con theo năm.
    """
    
    score_col = f'Điểm TB {subject}'
    nam_thi_str = str(nam_thi)

    if score_col not in df_input.columns:
        return

    # 1. Tiền xử lý: Sắp xếp dữ liệu theo điểm môn học giảm dần
    df_viz = df_input.sort_values(by=score_col, ascending=False).copy()
    
    # 2. Xử lý đường dẫn lưu file
    year_output_dir = os.path.join(output_dir, nam_thi_str)
    os.makedirs(year_output_dir, exist_ok=True)
    file_output_png = os.path.join(year_output_dir, f'diem_tb_{subject}.png')

    # 3. Trực quan hóa (Horizontal Bar Chart)
    sns.set_style("whitegrid") 
    num_provinces = len(df_viz)
    
    # Kích thước figure: Tỷ lệ với số lượng tỉnh (63)
    fig, ax = plt.subplots(figsize=(10, num_provinces * 0.25)) 

    # Đảo ngược dữ liệu cho biểu đồ thanh ngang
    provinces = df_viz['Tỉnh/Thành phố'].values[::-1]
    scores = df_viz[score_col].values[::-1]

    # === ÁP DỤNG LOGIC MÀU SẮC TỪ HÀM GỐC ===
    # Sử dụng bảng màu tab10 của Seaborn (sẽ lặp lại 10 màu)
    colors = sns.color_palette("tab10", num_provinces) 
    
    ax.barh(provinces, 
            scores, 
            color=colors[::-1]) # Đảo ngược màu để phù hợp với việc đảo ngược thứ tự tỉnh

    # Đặt tên tiêu đề
    ax.set_title(f'Thứ hạng Điểm Trung bình Môn {subject} theo tỉnh ({nam_thi_str})', 
                 fontsize=14, 
                 fontweight='bold')

    # Thêm nhãn giá trị (score) lên từng thanh
    for i, (score, city) in enumerate(zip(df_viz[score_col], df_viz['Tỉnh/Thành phố'])):
        ax.text(score + 0.005, num_provinces - 1 - i, f'{score:.3f}', 
                va='center', 
                fontsize=8)

    # Cải thiện Trục X và Loại bỏ khung
    min_score = df_viz[score_col].min()
    max_score = df_viz[score_col].max()
    x_min_limit = max(0, min_score - 0.2) 
    ax.set_xlim(x_min_limit, max_score + 0.1)
    
    ax.set_xlabel(f'Điểm TB {subject}')
    sns.despine(left=False, bottom=True)

    # 4. Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(file_output_png)
    plt.close(fig) 
    print(f" -> Đã lưu: {os.path.basename(file_output_png)}")