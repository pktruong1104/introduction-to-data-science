# ok
import pandas as pd
import numpy as np
import os
import json
import requests
import time
from dotenv import load_dotenv
# ======================= CONFIG ===========================
CUC_NAM, CUC_BAC, CUC_DONG, CUC_TAY = 8, 24, 110, 102

# STEP này có thể điều chỉnh cho phù hợp 
STEP = 0.5

FILE_PATHS_NEW = [
    '../data/diem_thi_2019_new.csv',
    '../data/diem_thi_2020_new.csv',
    '../data/diem_thi_2021_new.csv',
    '../data/diem_thi_2022_new.csv',
    '../data/diem_thi_2023_new.csv',
    '../data/diem_thi_2024_new.csv',
]

# Danh sách tỉnh thành Việt Nam
provinces = [
    {'code': '01', 'name': 'Hà Nội'},
    {'code': '02', 'name': 'Thành phố Hồ Chí Minh'},
    {'code': '03', 'name': 'Hải Phòng'},
    {'code': '04', 'name': 'Đà Nẵng'},
    {'code': '05', 'name': 'Hà Giang'},
    {'code': '06', 'name': 'Cao Bằng'},
    {'code': '07', 'name': 'Lai Châu'},
    {'code': '08', 'name': 'Lào Cai'},
    {'code': '09', 'name': 'Tuyên Quang'},
    {'code': '10', 'name': 'Lạng Sơn'},
    {'code': '11', 'name': 'Bắc Kạn'},
    {'code': '12', 'name': 'Thái Nguyên'},
    {'code': '13', 'name': 'Yên Bái'},
    {'code': '14', 'name': 'Sơn La'},
    {'code': '15', 'name': 'Phú Thọ'},
    {'code': '16', 'name': 'Vĩnh Phúc'},
    {'code': '17', 'name': 'Quảng Ninh'},
    {'code': '18', 'name': 'Bắc Giang'},
    {'code': '19', 'name': 'Bắc Ninh'},
    {'code': '21', 'name': 'Hải Dương'},
    {'code': '22', 'name': 'Hưng Yên'},
    {'code': '23', 'name': 'Hòa Bình'},
    {'code': '24', 'name': 'Hà Nam'},
    {'code': '25', 'name': 'Nam Định'},
    {'code': '26', 'name': 'Thái Bình'},
    {'code': '27', 'name': 'Ninh Bình'},
    {'code': '28', 'name': 'Thanh Hóa'},
    {'code': '29', 'name': 'Nghệ An'},
    {'code': '30', 'name': 'Hà Tĩnh'},
    {'code': '31', 'name': 'Quảng Bình'},
    {'code': '32', 'name': 'Quảng Trị'},
    {'code': '33', 'name': 'Thừa Thiên Huế'},
    {'code': '34', 'name': 'Quảng Nam'},
    {'code': '35', 'name': 'Quảng Ngãi'},
    {'code': '36', 'name': 'Kon Tum'},
    {'code': '37', 'name': 'Bình Định'},
    {'code': '38', 'name': 'Gia Lai'},
    {'code': '39', 'name': 'Phú Yên'},
    {'code': '40', 'name': 'Đắk Lắk'},
    {'code': '41', 'name': 'Khánh Hòa'},
    {'code': '42', 'name': 'Lâm Đồng'},
    {'code': '43', 'name': 'Bình Phước'},
    {'code': '44', 'name': 'Bình Dương'},
    {'code': '45', 'name': 'Ninh Thuận'},
    {'code': '46', 'name': 'Tây Ninh'},
    {'code': '47', 'name': 'Bình Thuận'},
    {'code': '48', 'name': 'Đồng Nai'},
    {'code': '49', 'name': 'Long An'},
    {'code': '50', 'name': 'Đồng Tháp'},
    {'code': '51', 'name': 'An Giang'},
    {'code': '52', 'name': 'Bà Rịa-Vũng Tàu'},
    {'code': '53', 'name': 'Tiền Giang'},
    {'code': '54', 'name': 'Kiên Giang'},
    {'code': '55', 'name': 'Cần Thơ'},
    {'code': '56', 'name': 'Bến Tre'},
    {'code': '57', 'name': 'Vĩnh Long'},
    {'code': '58', 'name': 'Trà Vinh'},
    {'code': '59', 'name': 'Sóc Trăng'},
    {'code': '60', 'name': 'Bạc Liêu'},
    {'code': '61', 'name': 'Cà Mau'},
    {'code': '62', 'name': 'Điện Biên'},
    {'code': '63', 'name': 'Đắk Nông'},
    {'code': '64', 'name': 'Hậu Giang'}
]

output_dir = "../data/"
# =================== LẤY DATA CHO TỈNH =====================
# Token xác thực
load_dotenv()
MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN')

def geocode_province(province_name, token, *, session=None, timeout=10, debug=False):
    """
    Lấy tọa độ tỉnh/thành từ Mapbox Geocoding API (KHÔNG in token).
    Trả về (lat, lon) hoặc (None, None)
    """
    # Chặn trường hợp truyền nhầm list/dict vào đây
    if not isinstance(province_name, str):
        if debug:
            print(f"[geocode_province] province_name phải là string, nhận {type(province_name)}")
        return None, None

    province_name = province_name.strip()
    if not province_name:
        return None, None

    # Encode query cho an toàn
    query = quote(f"{province_name}, Vietnam")
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

    params = {
        "access_token": token,
        "country": "VN",
        "types": "region,place",
        "limit": 1,
    }

    sess = session or requests

    try:
        r = sess.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()

        features = data.get("features") or []
        if not features:
            if debug:
                print(f"Không tìm thấy tọa độ cho: {province_name}")
            return None, None

        lon, lat = features[0]["center"]
        return round(lat, 4), round(lon, 4)

    except requests.exceptions.HTTPError as e:
        # KHÔNG print(e) vì e chứa full URL -> lộ token
        status = getattr(e.response, "status_code", None)
        if debug:
            print(f"Lỗi HTTP khi lấy tọa độ cho {province_name} (status={status})")
        return None, None

    except requests.exceptions.RequestException as e:
        # KHÔNG print(e) vì có thể chứa URL
        if debug:
            print(f"Lỗi mạng khi lấy tọa độ cho {province_name}: {type(e).__name__}")
        return None, None


def crawl_province(provinces, mapbox_token, output_dir, *, sleep_sec=0.1, debug=False):
    results = []

    print("Bắt đầu lấy tọa độ các tỉnh thành Việt Nam...")
    print("-" * 60)

    os.makedirs(output_dir, exist_ok=True)

    with requests.Session() as session:
        for i, province in enumerate(provinces, 1):
            name = province.get("name")
            code = province.get("code")

            print(f"[{i}/{len(provinces)}] Đang lấy: {name}: ", end="")

            lat, lon = geocode_province(
                name, mapbox_token, session=session, debug=debug
            )

            if lat is not None and lon is not None:
                results.append({
                    "MA_TINH": code,
                    "TEN_TINH": name,
                    "VI_DO": lat,
                    "KINH_DO": lon,
                })
                print(f"({lat}, {lon})")
            else:
                print("Thất bại")

            time.sleep(sleep_sec)

    print("-" * 60)
    print(f"Hoàn thành! Đã lấy được {len(results)}/{len(provinces)} tỉnh thành")

    df = pd.DataFrame(results)
    output_file = os.path.join(output_dir, "province.csv")
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Ghi vào file .csv thành công: {output_file}")

    return df

# =================== TẠO GRID CHO TỈNH =====================
def create_grid_table(pd_province):
    pd_province['MA_TINH'] = pd_province['MA_TINH'].astype(str).str.zfill(2)
    pd_province['GRID_X'] = np.floor((pd_province['KINH_DO'] - CUC_TAY) / STEP).astype(int)
    pd_province['GRID_Y'] = np.floor((pd_province['VI_DO'] - CUC_NAM) / STEP).astype(int)
    pd_province['GRID_ID'] = pd_province['GRID_X'].astype(str) + '_' + pd_province['GRID_Y'].astype(str)
    return pd_province[['MA_TINH', 'TEN_TINH', 'GRID_ID']]

# ========= ÁNH XẠ GRID_ID CHO THÍ SINH =================
def calculate_gridId_Province(df, pd_province_grid):
    df['MA_TINH'] = df['MA_TINH'].astype(str).str.zfill(2)
    return pd.merge(df, pd_province_grid[['MA_TINH', 'GRID_ID']], on='MA_TINH', how='left')

# ========= LẤY TOP 2  =================
def get_top_n_fast(df, top_n):
    """
    Lấy 2 khối có điểm cao nhất cho mỗi thí sinh
    """
    df_sorted = df.sort_values(['SBD', 'DIEM_THI'], ascending=[True, False])
    df_top2 = df_sorted.groupby('SBD').head(top_n)
    return df_top2.reset_index(drop=True)

# ========================= DATA PREPROCESSING ============================
'''
    cut_off: lấy từ điểm đó trở lên
    step: chia mốc điểm 
    ko cần grid_id cho bảng dữ liệu nữa + mỗi năm một file. 
'''
def process_files_vectorized(cut_off=15.00, step=0.05):
    print("Đang load dữ liệu tỉnh...")
    pd_province = pd.read_csv('../data/province.csv')
    pd_province_grid = create_grid_table(pd_province)

    with open('../data/to_hop.json', 'r', encoding='utf-8') as f:
        to_hop = json.load(f)
    

    output_dir = "../data/"
    os.makedirs(output_dir, exist_ok=True)

    # Dictionary để lưu data của tất cả các năm
    year_data = {}

    # Xử lý từng file năm
    for file_path in FILE_PATHS_NEW:
        print(f"\n{'='*60}")
        print(f"Đang xử lý file: {file_path}")
        print(f"{'='*60}")
        
        df = pd.read_csv(file_path)
        print(f"Số dòng ban đầu: {len(df):,}")
        
        df = calculate_gridId_Province(df, pd_province_grid)

        all_scores = []
        
        for nam_thi_group, group_df in df.groupby('NĂM_THI'):
            to_hop_year = to_hop 
            print(f"\nNăm {nam_thi_group}: {len(group_df):,} thí sinh")
            
            # Tính điểm tất cả khối vectorized
            for khoi, subjects in to_hop_year.items():
                subjects_exist = [s for s in subjects if s in group_df.columns]
                if not subjects_exist:
                    continue
                
                temp = group_df[['SBD','MA_TINH','NĂM_THI','GRID_ID'] + subjects_exist].copy()

                # Bỏ dòng có môn NaN hoặc <=0
                mask = temp[subjects_exist].notna().all(axis=1) & (temp[subjects_exist] > 0).all(axis=1)
                temp = temp[mask]
                if temp.empty:
                    continue

                temp['KHOI_THI'] = khoi
                temp['DIEM_THI'] = temp[subjects_exist].sum(axis=1)
                all_scores.append(temp[['SBD','MA_TINH','NĂM_THI','GRID_ID','KHOI_THI','DIEM_THI']])
                
                print(f"  Khối {khoi}: {len(temp):,} thí sinh hợp lệ")

            if not all_scores:
                print("Không có dữ liệu hợp lệ!")
                continue

            df_all = pd.concat(all_scores, ignore_index=True)
            print(f"\nTổng số records sau khi tính điểm: {len(df_all):,}")

            # Lấy top 2 khối cho mỗi thí sinh
            print("Đang lấy top 2 khối cho mỗi thí sinh...")
            df_topn = get_top_n_fast(df_all, top_n=2)
            print(f"Sau khi lấy top 2: {len(df_topn):,} records")
            
            # Chia mốc phân vị
            bins = list(np.arange(cut_off,  30.05, step))
            # từ 15.00 đến 30.00 với bước 0.05
            records = []
            for moc in bins: 
                temp = df_topn[df_topn['DIEM_THI'] >= moc].copy()
                # Bỏ grid_id
                grouped = temp.groupby(['MA_TINH', 'NĂM_THI', 'KHOI_THI'], observed=True)['SBD'] \
                            .count().reset_index() 
                grouped['MOC_DIEM'] = moc
                records.append(grouped)
            df_summary = pd.concat(records,ignore_index=True) # ghép lại theo theo chiều dọc 
            df_summary = df_summary.rename(columns={'SBD': 'SO_THI_SINH'})
            
            # QUAN TRỌNG: Tính tổng thí sinh DUY NHẤT tham gia khối đó
            # (1 thí sinh chỉ tính 1 lần dù có thể có điểm ở nhiều khối)
            print("Đang tính tổng thí sinh duy nhất cho mỗi khối...")
            df_total = df_topn.groupby(['MA_TINH','NĂM_THI','KHOI_THI'], observed=True)['SBD'] \
                            .nunique().reset_index().rename(columns={'SBD':'TONG_THI_SINH'})
            # Định dạng lại cho mốc điểm
            df_summary['MOC_DIEM'] = df_summary['MOC_DIEM'].apply(lambda x: f"{x:.2f}")
            
            
            # Lưu vào dictionary theo năm thi
            if nam_thi_group not in year_data: 
                year_data[nam_thi_group] = []
            
            year_data[nam_thi_group].append(df_summary)
            print(f"Năm {nam_thi_group}: {len(df_summary):,} records ")
    
    # Gộp các tỉnh lại với nhau và export theo từng năm 
    print(f"\n{'='*60}")
    print("Đang export dữ liệu cho từng năm...")
    print(f"{'='*60}")
    
    for nam_thi, data_list in year_data.items():
        # Gộp tất cả các tỉnh của năm 
        df_year_all_provinces = pd.concat(data_list, ignore_index=True)
        
        # Sắp xếp theo tỉnh, khối, khoảng điểm 
        df_year_all_provinces = df_year_all_provinces.sort_values(['MA_TINH', 'KHOI_THI', 'MOC_DIEM']).reset_index(drop=True)

        
        # Ghi vào file csv cho từng năm
        output_file = os.path.join(output_dir, f"{nam_thi}_summary.csv")
        df_year_all_provinces.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        provinces  = df_year_all_provinces['MA_TINH'].unique()
        print(f"✓ Tỉnh {nam_thi}: {len(df_year_all_provinces):,} records, "
              f"Năm: {', '.join(map(str, sorted(provinces)))} → {output_file}")
    
    print(f"\n{'='*60}")
    print(f"Hoàn thành! Đã tạo {len(year_data)} file")
    print(f"{'='*60}")

if __name__ == "__main__":
    crawl_province()