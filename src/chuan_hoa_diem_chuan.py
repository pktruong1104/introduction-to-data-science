import re
import pandas as pd
import unicodedata
import os

# Chuyển đối dấu unicode
def remove_accents(s: str):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'D')

# Trích xuất môn chính
def detect_mon_chinh(ghichu: str):
    """
    Nhận dạng môn chính duy nhất.
    Chỉ xử lý dạng:
        - 'Môn chính: Toán'
        - 'Môn chính Toán'
    Mọi dạng 'nhân 2', 'nhân 3', 'hệ số', ... đều bị bỏ qua.
    """
    if not ghichu or pd.isna(ghichu):
        return None

    g = str(ghichu).strip()

    # Chỉ nhận dạng "Môn chính"
    m = re.search(r"môn\s*chính[:\s]+(.+)", g, re.IGNORECASE)
    if m:
        mon_raw = m.group(1).strip()

        # Làm sạch
        mon_raw = re.split(r"[,.;()]", mon_raw)[0].strip()   # bỏ phần sau dấu phẩy
        mon_raw = re.sub(r"\s+", " ", mon_raw)

        return remove_accents(mon_raw).upper()

    # Không phải môn chính → bỏ qua hoàn toàn
    return None

# Xử lí những tổ hợp đặc biệt
def extract_to_hop(raw: str) -> str:
    """
    Nhận chuỗi Tổ hợp môn (có thể có ngoặc, khoảng trắng, dấu phân tách khác nhau)
    Trả về chuỗi chuẩn: TOÁN;ANH;C03;C04;GDKTPL
    Loại bỏ tất cả dấu '(' và ')'.
    """
    if raw is None or raw == "":
        return ""

    # Loại bỏ tất cả '(' và ')'
    raw = raw.replace("(", "").replace(")", "").strip()

    # Chuẩn hóa các dấu phân tách thành ';'
    parts = re.split(r"[;,/|]+", raw)
    parts = [p.strip() for p in parts if p.strip()]

    # Trả về dạng TOÁN;ANH;C03...
    return ";".join(parts)

# Khối_môn chính
def normalize_tohop(raw, mon_chinh=None):
    if not raw or pd.isna(raw):
        return ""
    s = str(raw).upper().strip().replace(" ", "")
    khoi_list = re.split(r"[;,/|]+", s)
    khoi_list = [k for k in khoi_list if k]
    if not mon_chinh:
        return ";".join(sorted(set(khoi_list)))
    mon = remove_accents(mon_chinh).upper()
    new_list = []
    for k in khoi_list:
        if mon not in k:
            new_list.append(f"{k}_{mon}")
        else:
            new_list.append(k)
    return ";".join(sorted(set(new_list)))

# Chuẩn hóa mã ngành
def normalize_major_code_logic_substring(current_code, last_valid_base, ma_truong=None):
    """
    - Nếu mã ngành BẮT ĐẦU bằng mã trường → giữ nguyên, không chạy logic 7 số.
      VD: QHX01  (mã trường = QHX)
    - Nếu chứa chuỗi 7 chữ số → dùng làm base.
    - Nếu không → ghép base trước đó.
    """
    ma = str(current_code).strip()
    if not ma or ma.lower() == "nan":
        return "", last_valid_base

    # Nếu mã ngành bắt đầu bằng mã trường
    if ma_truong and isinstance(ma_truong, str):
        mt = ma_truong.strip().upper()
        if ma.upper().startswith(mt):
            # Không đụng vào logic 7 số → giữ nguyên chuỗi
            return ma, last_valid_base

    # Tách 7 chữ số như trước
    match = re.search(r"(\d{7})", ma)
    if match:
        new_base = match.group(1)
        return ma, new_base

    # Không có 7 số thì ghép base cũ
    if last_valid_base:
        if ma.startswith("_"):
            return f"{last_valid_base}{ma}", last_valid_base
        else:
            return f"{last_valid_base}_{ma}", last_valid_base

    # Không có base → trả về nguyên
    return ma, last_valid_base

# Xóa tất cả khoảng trắng trong mã ngành
def remove_whitespace_major(code: str) -> str:
    if not isinstance(code, str) or not code:
        return code
    return code.replace(" ", "")

# Chuẩn hóa tên ngành
def chuan_hoa_ten_nganh(name: str) -> str:
    if not name or pd.isna(name):
        return ""

    name = str(name).strip()

    # Tách phần trước ngoặc và phần trong ngoặc
    m = re.match(r"^(.*?)(\s*\(.*\))?$", name)
    if not m:
        return name

    main = m.group(1).strip()            # phần tên ngành
    extra = m.group(2) if m.group(2) else ""   # phần trong ngoặc (giữ nguyên)

    # Chuẩn hoá phần tên ngành: viết hoa chữ cái đầu của mỗi từ
    main = " ".join([w.capitalize() for w in main.split()])

    return f"{main} {extra}".strip()


# Lọc ngành có điểm đủ từ năm 2019 - 2025       
def filter_major_full_years(df_clean, path_loai):
    """
    Lọc ra các mã ngành (theo Mã trường + Mã ngành) có đủ
    toàn bộ các năm 2019 → 2025.
    Đồng thời lưu các hàng bị loại vào file CSV.
    """
    REQUIRED_YEARS = {2019, 2020, 2021, 2022, 2023, 2024, 2025}

    # Xác định các nhóm hợp lệ
    valid_groups = df_clean.groupby(["Mã trường", "Mã ngành"])["Năm xét tuyển"].apply(
        lambda years: REQUIRED_YEARS.issubset(set(years))
    )
    valid_indices = valid_groups[valid_groups].index

    # DataFrame cuối cùng chỉ chứa các nhóm hợp lệ
    df_final = (
        df_clean.set_index(["Mã trường", "Mã ngành"])
                .loc[valid_indices]
                .reset_index()
                .sort_values(by=["Mã trường", "Mã ngành", "Năm xét tuyển"])
    )

    # Lưu các hàng bị loại
    df_removed = df_clean.set_index(["Mã trường", "Mã ngành"]).drop(valid_indices).reset_index()
    df_removed.to_csv(path_loai, index=False, encoding="utf-8-sig")

    return df_final

def apply_major_khoi(df):
    """
    Chỉ tách thành mã ngành_khối khi:
        - Cùng Mã trường
        - Cùng Mã ngành
        - Cùng Năm xét tuyển
        - Có >= 2 tổ hợp môn
    """

    # Đếm số tổ hợp theo (Mã trường, Mã ngành, Năm xét tuyển)
    group_counts = (
        df.groupby(["Mã trường", "Mã ngành", "Năm xét tuyển"])["Tổ hợp môn"]
        .nunique()
    )

    # Những nhóm đa khối (>= 2 tổ hợp)
    multi_keys = set(group_counts[group_counts > 1].index)

    result_rows = []

    for _, r in df.iterrows():
        key = (r["Mã trường"], r["Mã ngành"], r["Năm xét tuyển"])
        khoi_list = str(r["Tổ hợp môn"]).split(";")

        if key in multi_keys:
            # → Ngành này NĂM NÀY có nhiều khối → tách ra
            for khoi in khoi_list:
                result_rows.append({
                    **r.to_dict(),
                    "Mã ngành": f"{r['Mã ngành']}_{khoi}",
                    "Tổ hợp môn": khoi
                })
        else:
            # → Không thỏa 4 điều kiện → giữ nguyên
            result_rows.append(r.to_dict())

    return pd.DataFrame(result_rows)

def process_diem_chuan(path_input, path_output):
    print(f"Đang đọc dữ liệu từ: {path_input}")
    try:
        df = pd.read_csv(path_input, dtype=str).fillna("")
    except FileNotFoundError:
        print("Không tìm thấy file.")
        return

    clean_rows = []
    current_base_id = ""

    # 1) Chuẩn hóa dữ liệu từng dòng
    for _, r in df.iterrows():
        ma_raw = r.get("Mã ngành", "")
        ma_raw = remove_whitespace_major(ma_raw) # Xóa khoảng trắng
        # Chuẩn hóa mã ngành
        ten = r.get("Tên ngành", "")
        tohop = extract_to_hop(r.get("Tổ hợp môn", ""))
        score = r.get("Điểm chuẩn", "")
        school = r.get("Mã trường", "")
        ghichu = r.get("Ghi chú", "")
        ma_final, new_base = normalize_major_code_logic_substring(ma_raw, current_base_id,school)
        if new_base:
            current_base_id = new_base

        # môn chính
        mon_chinh = detect_mon_chinh(ghichu)
        tohop_norm = normalize_tohop(tohop, mon_chinh)
        ten = chuan_hoa_ten_nganh(ten)
        # năm
        y_match = re.search(r"20\d{2}", str(r.get("Năm xét tuyển", "")))
        year = int(y_match.group(0)) if y_match else 0

        clean_rows.append({
            "Mã trường": school,
            "Mã ngành": ma_final,
            "Tên ngành": ten,
            "Tổ hợp môn": tohop_norm,
            "Điểm chuẩn": score,
            "Năm xét tuyển": year,
            "Ghi chú": ghichu,
            "Môn chính": mon_chinh if mon_chinh else ""
        })
    # tạo DataFrame chuẩn hóa bước 1
    df_clean = pd.DataFrame(clean_rows)

    # Lọc ngành có điểm từ 2019–2025
    print("Đang lọc dữ liệu đủ 7 năm (2019-2025)...")
    df_clean = filter_major_full_years(df_clean, r"C:\Users\ADMIN\OneDrive - VNU-HCMUS\Documents\GitHub\introduction-to-data-science\data\diem_chuan_bi_loai.csv")

    # Áp dụng tách ngành_khối
    df_final = apply_major_khoi(df_clean)

    df_final.to_csv(path_output, index=False, encoding="utf-8-sig")
    print(f"Hoàn tất! File lưu tại: {path_output}")

    return df_final

if __name__ == "__main__":
    INPUT_PATH = r"C:\Users\ADMIN\OneDrive - VNU-HCMUS\Documents\GitHub\introduction-to-data-science\data\diem_chuan_all.csv"
    OUTPUT_PATH = r"C:\Users\ADMIN\OneDrive - VNU-HCMUS\Documents\GitHub\introduction-to-data-science\data\diem_chuan_chuan_hoa.csv"
    process_diem_chuan(INPUT_PATH, OUTPUT_PATH)
