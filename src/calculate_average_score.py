import pandas as pd
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns


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

def visualize_average_score_ranking(file_input_csv, nam_thi, file_output_png='diem_trung_binh_xep_hang.png'):
    """
    Tạo biểu đồ thanh ngang xếp hạng điểm trung bình thi THPT theo tỉnh.

    Tham số:
    - file_input_csv (str): Đường dẫn đến file CSV kết quả (ví dụ: 'diem_trung_binh_2024.csv')
                            File này phải có các cột: 'Tỉnh/Thành phố' và 'Điểm trung bình (Năm)'
    - nam_thi (int/str): Năm của dữ liệu (ví dụ: 2024). Dùng để đặt tiêu đề cột.
    - file_output_png (str): Tên file PNG để lưu biểu đồ.

    Trả về:
    - None (Chỉ lưu file ảnh)
    """
    try:
        # 1. Đọc dữ liệu
        df = pd.read_csv(file_input_csv)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file dữ liệu '{file_input_csv}'")
        return

    score_col = f'Điểm trung bình ({nam_thi})'
    
    # Kiểm tra xem cột điểm có tồn tại không
    if score_col not in df.columns:
        print(f"Lỗi: Không tìm thấy cột điểm '{score_col}' trong file.")
        return

    # 2. Tiền xử lý dữ liệu cho Visualization
    # Đảm bảo cột điểm là kiểu số và sắp xếp
    df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
    df_viz = df.sort_values(by=score_col, ascending=False).copy()

    # 3. Trực quan hóa (Horizontal Bar Chart)
    sns.set_style("whitegrid") 

    # Kích thước figure tỷ lệ với số lượng tỉnh (mỗi tỉnh chiếm 0.4 đơn vị chiều cao)
    fig, ax = plt.subplots(figsize=(10, len(df_viz) * 0.4)) 

    # Đảo ngược dữ liệu cho biểu đồ thanh ngang để điểm cao nhất nằm trên cùng
    provinces = df_viz['Tỉnh/Thành phố'].values[::-1]
    scores = df_viz[score_col].values[::-1]

    # Vẽ biểu đồ thanh ngang
    ax.barh(provinces, 
            scores, 
            color=sns.color_palette("tab10", len(df_viz))) 

    # Đặt tên tiêu đề
    ax.set_title(f'Điểm trung bình thi Tốt nghiệp THPT theo tỉnh ({nam_thi})', 
                 fontsize=16, 
                 fontweight='bold')

    # Thêm nhãn giá trị (score) lên từng thanh
    for i, (score, city) in enumerate(zip(df_viz[score_col], df_viz['Tỉnh/Thành phố'])):
        ax.text(score + 0.005, len(df_viz) - 1 - i, f'{score:.3f}', 
                va='center', 
                fontsize=10, 
                fontweight='bold')

    # Cải thiện trục X (giới hạn)
    # Giới hạn trục x để biểu đồ không quá nhỏ hoặc quá lớn
    min_score = df_viz[score_col].min()
    max_score = df_viz[score_col].max()
    ax.set_xlim(min_score - 0.05, max_score + 0.1)
    ax.set_xlabel('Điểm trung bình')

    # Loại bỏ khung bên phải và bên trên
    sns.despine(left=False, bottom=True)

    # 4. Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(file_output_png)
    print(f"Đã tạo file biểu đồ: {file_output_png}")

def create_ranking_journey_table(project_root, list_years, target_year=2024, top_n=10, is_top_n_best=True):
    """
    Tạo bảng theo dõi hành trình thứ hạng, linh hoạt chọn Top N Tốt nhất hoặc Tệ nhất.

    Tham số:
    - project_root (str): Đường dẫn thư mục gốc.
    - list_years (range/list): Danh sách các năm cần phân tích.
    - target_year (int): Năm dùng để xác định Top N.
    - top_n (int): Số lượng tỉnh Top đầu/cuối cần theo dõi.
    - is_top_n_best (bool): 
        - True: Lấy Top N Tốt nhất (Điểm cao, Rank thấp).
        - False: Lấy Top N Tệ nhất (Điểm thấp, Rank cao).

    Trả về:
    - DataFrame: Bảng thứ hạng hành trình đã được lọc và sắp xếp.
    """
    all_ranks = []
    
    # 1. Gộp Dữ liệu và Tính Thứ hạng 
    for nam in list_years:
        file_path = os.path.join(project_root, 'data', f'diem_trung_binh_{nam}.csv')
        
        if os.path.exists(file_path):
            df_year = pd.read_csv(file_path)
            score_col = f'Điểm trung bình ({nam})'
            
            df_year[score_col] = pd.to_numeric(df_year[score_col], errors='coerce')
            df_year = df_year.sort_values(by=score_col, ascending=False).reset_index(drop=True)
            df_year['Rank'] = df_year.index + 1 
            
            new_rank_col_name = f'Thứ hạng {nam}'
            df_year = df_year.rename(columns={'Rank': new_rank_col_name})
            df_year = df_year[['Tỉnh/Thành phố', new_rank_col_name]]
            all_ranks.append(df_year)


    if not all_ranks:
        return pd.DataFrame()

    # Gộp tất cả dữ liệu Rank
    df_merged = all_ranks[0]
    for df_rank in all_ranks[1:]:
        df_merged = pd.merge(df_merged, df_rank, on='Tỉnh/Thành phố', how='outer')

    # 3. XÁC ĐỊNH DANH SÁCH TỈNH MỤC TIÊU
    target_rank_col = f'Thứ hạng {target_year}'
    
    # Sắp xếp toàn bộ bảng theo thứ hạng của năm mục tiêu
    # Nếu lấy Top Tốt nhất (Rank thấp), sắp xếp tăng dần. Nếu lấy Tệ nhất (Rank cao), sắp xếp giảm dần.
    sort_ascending = is_top_n_best
    
    df_sorted_by_target = df_merged.sort_values(by=target_rank_col, 
                                                ascending=sort_ascending, 
                                                na_position='last')
    
    # Lọc Top N tỉnh cần theo dõi (dù là Top Tốt nhất hay Top Tệ nhất)
    top_n_provinces = df_sorted_by_target.head(top_n)['Tỉnh/Thành phố'].tolist()

    # 4. Tạo Bảng Hành trình Thứ hạng (Ranking Journey Table)
    df_journey = df_merged[df_merged['Tỉnh/Thành phố'].isin(top_n_provinces)].copy()
    
    # Sắp xếp lại bảng cuối cùng theo cùng thứ tự (ascending=sort_ascending)
    df_journey = df_journey.sort_values(by=target_rank_col, ascending=sort_ascending) 
    
    # Sắp xếp thứ tự cột
    column_order = ['Tỉnh/Thành phố'] + [f'Thứ hạng {nam}' for nam in list_years]
    df_journey = df_journey[column_order]
    
    df_journey = df_journey.fillna('-') 

    return df_journey

def visualize_ranking_journey(df_ranking_journey,custom_title=None, file_output_png='ranking_journey_chart.png'):
    """
    Vẽ biểu đồ đường thể hiện sự thay đổi thứ hạng của các tỉnh qua các năm.

    Tham số:
    - df_ranking_journey (DataFrame): Bảng thứ hạng hành trình đã được lọc và làm sạch.
    - title_suffix (str): Phần tiêu đề bổ sung (ví dụ: "Top 10 tỉnh (2024)").
    - file_output_png (str): Tên file PNG để lưu biểu đồ.
    """
    if df_ranking_journey.empty:
        print("Không có dữ liệu để trực quan hóa hành trình thứ hạng.")
        return

    # 1. Chuyển đổi dữ liệu từ định dạng rộng (wide) sang dài (long)
    # Lấy danh sách các cột năm thứ hạng
    rank_cols = [col for col in df_ranking_journey.columns if col.startswith('Thứ hạng')]
    
    # Sử dụng melt để chuyển đổi (unpivot)
    df_long = df_ranking_journey.melt(
        id_vars=['Tỉnh/Thành phố'], 
        value_vars=rank_cols,
        var_name='Năm', 
        value_name='Thứ hạng'
    )
    

    df_long['Năm'] = df_long['Năm'].str.replace('Thứ hạng ', '').astype(int)
    
    # Chuyển đổi cột 'Thứ hạng' sang kiểu số (bỏ qua giá trị '-')
    df_long['Thứ hạng'] = pd.to_numeric(df_long['Thứ hạng'], errors='coerce')
    
    # Loại bỏ các hàng bị thiếu (NaN) sau khi chuyển đổi (tức là các giá trị '-')
    df_long = df_long.dropna(subset=['Thứ hạng'])


    # 2. Vẽ biểu đồ đường
    sns.set_style("whitegrid")
    plt.figure(figsize=(14, 8))

    # Sử dụng Line Plot
    line_plot = sns.lineplot(
        data=df_long, 
        x='Năm', 
        y='Thứ hạng', 
        hue='Tỉnh/Thành phố',
        marker='o',
        linewidth=2
    )

    # Thêm nhãn giá trị (Annotation) lên từng điểm
    for index, row in df_long.iterrows():
        # Dùng vị trí X, Y (Năm, Thứ hạng) để đặt nhãn
        line_plot.text(
            row['Năm'], 
            row['Thứ hạng'] + 0.7, 
            f"{int(row['Thứ hạng'])}", 
            horizontalalignment='center', 
            size='small', 
            color=sns.color_palette()[df_long['Tỉnh/Thành phố'].unique().tolist().index(row['Tỉnh/Thành phố'])]
        )

    # ĐẶT TIÊU ĐỀ 
    
    # Nếu custom_title được truyền vào, sử dụng nó. Ngược lại, tạo tiêu đề mặc định.
    if custom_title:
        final_title = custom_title
    else:
        # Tạo tiêu đề mặc định (Ví dụ: Hành trình Thứ hạng của X tỉnh)
        num_provinces = len(df_ranking_journey['Tỉnh/Thành phố'].unique())
        min_year = df_long['Năm'].min()
        max_year = df_long['Năm'].max()
        final_title = f'Hành trình Thứ hạng của {num_provinces} tỉnh từ {min_year} đến {max_year}'


    plt.title(final_title, fontsize=16, fontweight='bold')
            
    # Đảo ngược trục Y (thứ hạng)
    # Trong xếp hạng, Rank 1 là tốt nhất, nên nó phải nằm ở trên cùng.
    plt.gca().invert_yaxis()
    
    # Thiết lập trục
    #plt.title(f'Hành trình Thứ hạng Thi THPT qua các năm ({title_suffix})', fontsize=16, fontweight='bold')
    plt.xlabel("Năm")
    plt.ylabel("Thứ hạng (Rank 1 là tốt nhất)")
    plt.xticks(df_long['Năm'].unique().astype(int)) # Đảm bảo trục x hiển thị các năm chính xác
    plt.legend(title='Tỉnh/Thành phố', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    plt.savefig(file_output_png)
    print(f"Đã tạo biểu đồ hành trình: {file_output_png}")
    plt.show()

def clean_rank_to_int(df_in):
    """Làm sạch DataFrame Rank, chuyển đổi các cột rank sang kiểu số nguyên, 
       và giữ lại các giá trị '-' hoặc 'N/A'."""
    
    df = df_in.copy()
    
    # Hàm chuyển đổi Rank sang int, giữ nguyên '-'
    def convert_rank(val):
        if pd.isna(val) or val == '-':
            return '-'
        try:
            # Chuyển đổi từ float (ví dụ: 10.0) sang int
            return int(float(val))
        except (ValueError, TypeError):
            return '-'

    # Áp dụng làm sạch cho các cột rank
    for col in df.columns:
        if col != 'Tỉnh/Thành phố': 
            df[col] = df[col].apply(convert_rank)
            
    # Xóa cột Index (Các số 55, 34, 32...) nếu nó vô tình bị giữ lại
    if df.columns[0] != 'Tỉnh/Thành phố':
        df = df.iloc[:, 1:]
        
    return df