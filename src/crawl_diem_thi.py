import requests
from bs4 import BeautifulSoup
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import glob
import os

# ==== Đường dẫn thư mục ====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../project
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)  # Tạo thư mục nếu chưa có


# ==== Crawl dữ liệu ====
def get_diem_thi(ma_tinh, sbd_num, nam_thi=2025):
    """
    Trả về dict {MA_TINH, SBD, NAM_THI, điểm các môn} hoặc None nếu không có kết quả
    
    Args:
        ma_tinh (str/int): Mã tỉnh (ví dụ: '01').
        sbd_num (int): Số báo danh (phần số, ví dụ: 123).
        nam_thi (int): Năm thi cần tra cứu (Mặc định là 2025).
    """
    sbd = f"{ma_tinh}{sbd_num:06d}"
    
    url = f"https://vietnamnet.vn/giao-duc/diem-thi/tra-cuu-diem-thi-tot-nghiep-thpt/{nam_thi}/{sbd}.html"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("div.resultSearch__right table")
        if not table:
            return None

        result = {
            "NĂM_THI": nam_thi, 
            "MA_TINH": ma_tinh, 
            "SBD": sbd
        }
        
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) == 2:
                mon = cols[0].text.strip()
                diem = cols[1].text.strip()
                result[mon] = diem
        return result

    except Exception as e:
        print(f"Lỗi: {e}")
        return None

# ==== Crawl 1 tỉnh ====
def crawl_tinh(ma_tinh, nam_thi=2025, max_empty=100, max_workers=20):
    """
    Crawl toàn bộ thí sinh của 1 tỉnh theo năm.
    Args:
        ma_tinh: Mã tỉnh.
        nam_thi: Năm thi (Mặc định 2025).
        max_empty: Số lượng SBD rỗng liên tiếp để dừng.
        max_workers: Số luồng chạy song song.
    """
    
    output = os.path.join(DATA_DIR, f"diem_thi_{nam_thi}_{ma_tinh}.csv")
    print(f" Bắt đầu crawl tỉnh {ma_tinh} - Năm {nam_thi}...")

    with open(output, "w", newline="", encoding="utf-8") as f:
        fieldnames = [ "NĂM_THI","MA_TINH", "SBD", "Toán", "Văn", "Ngoại ngữ", "Lí", "Hóa", "Sinh",
                      "Sử", "Địa", "GDCD", "Giáo dục kinh tế pháp luật", "Tin",
                      "Công nghệ nông nghiệp", "Công nghệ công nghiệp"]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        empty_count = 0
        batch_size = 100
        sbd_num = 1

        while True:
            sbd_batch = [sbd_num + i for i in range(batch_size)]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(get_diem_thi, ma_tinh, num, nam_thi): num 
                    for num in sbd_batch
                }

                for future in as_completed(futures):
                    data = future.result()
                    if data:
                        data['NĂM_THI'] = nam_thi
                        
                        writer.writerow(data)
                        diem_co_thuc = {k: v for k, v in data.items() if k not in ['NĂM_THI', 'MA_TINH', 'SBD'] and v}
                        print(f" SBD {data['SBD']}: {diem_co_thuc}")
                        empty_count = 0
                    else:
                        empty_count += 1

                    # Kiểm tra điều kiện dừng
                    if empty_count >= max_empty:
                        print(f" Hết thí sinh tại tỉnh {ma_tinh} (Năm {nam_thi})")
                        return

            sbd_num += batch_size
            time.sleep(1) 


# ==== Crawl nhiều tỉnh ====
def crawl_nhieu_tinh(start_tinh=1, end_tinh=64, nam_thi=2025):
    """
    Crawl dữ liệu của một danh sách các tỉnh theo năm.
    
    Args:
        start_tinh (int): Mã tỉnh bắt đầu (ví dụ: 1).
        end_tinh (int): Mã tỉnh kết thúc (ví dụ: 64).
        nam_thi (int): Năm thi cần crawl (Mặc định: 2025).
    """
    print(f"--- BẮT ĐẦU CRAWL TOÀN QUỐC NĂM {nam_thi} ---")
    
    for id_tinh in range(start_tinh, end_tinh + 1):
        ma_tinh_str = f"{id_tinh:02d}"
        
        try:
            crawl_tinh(ma_tinh=ma_tinh_str, nam_thi=nam_thi)
            print(f" Đã xong tỉnh {ma_tinh_str} (Năm {nam_thi})")
            
        except Exception as e:
            print(f" Lỗi tại tỉnh {ma_tinh_str}: {e}")
        
        # Nghỉ giữa các tỉnh để tránh quá tải server
        time.sleep(3)
    
    print(f"--- HOÀN TẤT NĂM {nam_thi} ---")


# ==== Gộp file ====
def merge_csv(folder_path=DATA_DIR, nam_thi=2025, output_file=None):
    """
    Gộp các file CSV thành phần theo NĂM THI cụ thể.
    
    Args:
        folder_path (str): Thư mục chứa data.
        nam_thi (int): Năm thi cần gộp (Ví dụ: 2025).
        output_file (str): Tên file đầu ra. Nếu để None, tự động đặt tên theo năm.
    """
    
    # Tự động đặt tên file output nếu người dùng không truyền vào
    if output_file is None:
        output_file = f"diem_thi_toan_quoc_{nam_thi}.csv"
    
    output_path = os.path.join(folder_path, output_file)


    # Giả sử file thành phần có dạng: diem_thi_2025_01.csv
    search_pattern = os.path.join(folder_path, f"diem_thi_{nam_thi}_*.csv")
    all_files = glob.glob(search_pattern)

    # Loại bỏ file output ra khỏi danh sách (đề phòng trùng tên gây vòng lặp)
    all_files = [f for f in all_files if os.path.basename(f) != output_file]

    if not all_files:
        print(f" Không tìm thấy file thành phần nào cho năm {nam_thi} trong {folder_path}")
        return

    print(f" Tìm thấy {len(all_files)} file dữ liệu năm {nam_thi}. Đang gộp...")

    merged_data = []
    for file in all_files:
        try:
            tmp = pd.read_csv(file)
            merged_data.append(tmp)
            print(f" - Đã nạp: {os.path.basename(file)}") 
        except Exception as e:
            print(f" Lỗi khi đọc file {file}: {e}")

    if merged_data:
        merged_df = pd.concat(merged_data, ignore_index=True)
        merged_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f" Đã gộp xong! File lưu tại: {output_path}")
        print(f" Tổng số dòng dữ liệu: {len(merged_df)}")
    else:
        print(" Danh sách dữ liệu rỗng.")

