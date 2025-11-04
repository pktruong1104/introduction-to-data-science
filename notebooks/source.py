import requests
from bs4 import BeautifulSoup
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd 
import glob
import os


#====================================================HÀM CHÍNH===============================================

def get_diem_thi(ma_tinh, sbd_num):
    """Trả về dict {MA_TINH, SBD, điểm các môn} hoặc None nếu không có kết quả"""
    sbd = f"{ma_tinh}{sbd_num:06d}"
    url = f"https://vietnamnet.vn/giao-duc/diem-thi/tra-cuu-diem-thi-tot-nghiep-thpt/2025/{sbd}.html"
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

        result = {"MA_TINH": ma_tinh, "SBD": sbd}
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) == 2:
                mon = cols[0].text.strip()
                diem = cols[1].text.strip()
                result[mon] = diem
        return result

    except Exception:
        return None


def crawl_tinh(ma_tinh, max_empty=100, max_workers=20):
    # max_workers: số luồng chạy -> tối ưu thời gian crawl 
    """Crawl toàn bộ thí sinh của 1 tỉnh (dừng khi gặp max_empty SBD liên tiếp không có dữ liệu)"""
    output = f"diem_thi_{ma_tinh}.csv"
    print(f"Bắt đầu crawl tỉnh {ma_tinh}...")

    with open(output, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["MA_TINH", "SBD", "Toán", "Văn", "Ngoại ngữ", "Lí", "Hóa", "Sinh", "Sử", "Địa", "GDCD","Giáo dục kinh tế pháp luật","Tin", "Công nghệ nông nghiệp", "Công nghệ công nghiệp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        empty_count = 0
        batch_size = 100

        sbd_num = 1
        while True:
            sbd_batch = [sbd_num + i for i in range(batch_size)]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(get_diem_thi, ma_tinh, num): num for num in sbd_batch}

                for future in as_completed(futures):
                    data = future.result()
                    if data:
                        writer.writerow(data)
                        print(f"{data['SBD']}: {list(data.keys())[2:]}")
                        empty_count = 0
                    else:
                        empty_count += 1

                    # Dừng nếu liên tiếp quá nhiều SBD rỗng (tức là đã hết thí sinh)
                    if empty_count >= max_empty:
                        print(f"Hết thí sinh tại tỉnh {ma_tinh}")
                        return

            sbd_num += batch_size
            time.sleep(1)


def crawl_toan_quoc(start_tinh=1, end_tinh=64):
    """Crawl toàn bộ 64 tỉnh/thành"""
    for ma_tinh in range(start_tinh, end_tinh + 1):
        crawl_tinh(f"{ma_tinh:02d}")
        print(f"Đã xong tỉnh {ma_tinh:02d}")
        time.sleep(3)  # nghỉ giữa các tỉnh

#=========================================HELPER===========================================

# Hàm merge các file csv lại 
def merge_csv(folder_path=".", output_file="diem_thi_toan_quoc.csv"): 
    '''
    Gộp tất cả file csv của các tỉnh vào một file cuối cùng 
    '''
    all_file = glob.glob(os.path.join(folder_path, "diem_thi_*.csv"))
    # tìm các file có bắt đầu diem_thi 
    if not all_file: 
        print(f"Không tìm thấy danh sách các file")
        return 
    
    root =[]
    for file in all_file: 
        try: 
            tmp = pd.read_csv(file)
            root.append(tmp)
            print("Nạp thành công")
        except Exception as e: 
            print(f"Lỗi khi đọc file {file}")
    # Gộp tất cả
    merged_df = pd.concat(root, ignore_index=True)

    # Lưu ra file tổng
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig")

# Hàm chia ra tỉnh để crawl 
def crawl_tinh_path(start_tinh=1, end_tinh=10): 
    for id_tinh in range(start_tinh, end_tinh+1): 
        ma_tinh_str = f"{id_tinh:02d}"
        crawl_tinh(ma_tinh_str,100,200)
        print(f"Đã xong tỉnh {ma_tinh_str}")
        time.sleep(3) 

if __name__ == "__main__":
    # test crawl với một thí sinh
    result = get_diem_thi(37, 1)
    # vì chỉ có 1 thí sinh nê bọc vào list 
    df = pd.DataFrame([result])

    print(df)
    # test crawl với tỉnh 
    # result_province = crawl_tinh(37)
    # df = pd.DataFrame(result_province)
    # print(df)

    # test merge_file 
    #merge_csv(folder_path=".", output_file="diem_thi_toanquoc.csv")

    # Test hàm chia tỉnh ra để crawl 
    # Quoc: 1-> 31 
    # Tuan: 32 -> 63 
    crawl_tinh_path(1,31)
    
