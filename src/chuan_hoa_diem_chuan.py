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
def normalize_major_code_logic_substring(current_code, last_valid_base):
    """
    Ý tưởng:
    - Tìm chuỗi 7 chữ số (\d{7}) bất kỳ trong mã.
    - Có: Cập nhật Base = 7 số đó. Trả về Mã gốc (Giữ nguyên).
    - Không: Trả về Base + Mã hiện tại.
    """
    ma = str(current_code).strip()
    if not ma or ma.lower() == 'nan':
        return "", last_valid_base

    # Tìm chuỗi 7 chữ số liên tiếp ở bất kỳ đâu trong chuỗi
    match = re.search(r"(\d{7})", ma)

    if match:
        # TRƯỜNG HỢP 1: CHỨA 7 SỐ (VD: "1234567CLC", "7850201", "F7480103")
        new_base = match.group(1)  # Lấy 7 số tìm thấy làm base (VD: 1234567)
        return ma, new_base        # Giữ nguyên mã input (1234567CLC)

    else:
        # TRƯỜNG HỢP 2: KHÔNG CHỨA 7 SỐ (VD: "TT", "DT", "EP01")
        if last_valid_base:
            # Nếu mã con đã bắt đầu bằng "_" thì chỉ ghép (tránh __)
            if ma.startswith('_'):
                return f"{last_valid_base}{ma}", last_valid_base
            else:
                # Nếu chưa có, thêm "_" vào giữa
                return f"{last_valid_base}_{ma}", last_valid_base
        else:
            # Không có base thì trả về nguyên gốc
            return ma, last_valid_base

# Lọc ngành có điểm đủ từ năm 2019 - 2025       
def filter_major_full_years(df_clean):
    """
    Lọc ra các mã ngành (theo Mã trường + Mã ngành) có đủ
    toàn bộ các năm 2019 → 2025.
    """
    REQUIRED_YEARS = {2019, 2020, 2021, 2022, 2023, 2024, 2025}

    valid_groups = df_clean.groupby(["Mã trường", "Mã ngành"])["Năm xét tuyển"].apply(
        lambda years: REQUIRED_YEARS.issubset(set(years))
    )

    valid_indices = valid_groups[valid_groups].index

    df_final = (
        df_clean.set_index(["Mã trường", "Mã ngành"])
                .loc[valid_indices]
                .reset_index()
                .sort_values(by=["Mã trường", "Mã ngành", "Năm xét tuyển"])
    )

    return df_final

# Sinh cột Mã ngành_Khối
def normalize_major_khoi(ma_nganh: str, tohop_norm: str) -> list[str]:
    """
    Sinh mã ngành theo từng khối.
    Nếu tổ hợp là: A00;A01;D01
    Trả về: 7310101_A00, 7310101_A01, 7310101_D01
    """
    if not ma_nganh:
        return []

    if not tohop_norm:
        return [ma_nganh]   # không có khối → ngành đơn (7310101)

    # Tách chuỗi tổ hợp thành danh sách các khối (A00, A01, D01)
    khoi_list = [k.strip() for k in tohop_norm.split(";") if k.strip()]

    # Trả về danh sách đã ghép mã ngành và khối (7310101_A00, ...)
    return [f"{ma_nganh}_{khoi}" for khoi in khoi_list]

def process_diem_chuan(path_input, path_output="diem_chuan_chuan_hoa.csv"):
    print(f"Đang đọc dữ liệu từ: {path_input}")
    try:
        df = pd.read_csv(path_input, dtype=str).fillna("")
    except FileNotFoundError:
        print("Không tìm thấy file.")
        return

    clean_rows = []
    current_base_id = ""

    for _, r in df.iterrows():
        ma_raw = r.get("Mã ngành", "")

        # Chuẩn hóa mã ngành
        ma_final, new_base = normalize_major_code_logic_substring(ma_raw, current_base_id)
        if new_base:
            current_base_id = new_base

        ten = r.get("Tên ngành", "")
        tohop = r.get("Tổ hợp môn", "")
        score = r.get("Điểm chuẩn", "")
        year_str = r.get("Năm xét tuyển", "")
        school = r.get("Mã trường", "")
        ghichu = r.get("Ghi chú", "")

        # Tìm môn chính
        mon_chinh = detect_mon_chinh(ghichu)
        # Chuẩn hóa tổ hợp môn kèm môn chính
        tohop = extract_to_hop(tohop)
        tohop_norm = normalize_tohop(tohop, mon_chinh)

        # Parse năm
        y_match = re.search(r"20\d{2}", str(year_str))
        year = int(y_match.group(0)) if y_match else 0

        # --- NEW: chuẩn hóa thành nhiều dòng cho từng khối ---
        ma_khoi_list = normalize_major_khoi(ma_final, tohop_norm)

        for mk in ma_khoi_list:
            if '_' in mk:
                th = mk.split('_', 1)[1]
            clean_rows.append({
                "Mã trường": school,
                "Mã ngành": ma_final,
                "Mã ngành_Khối": mk,
                "Tên ngành": ten,
                "Tổ hợp môn": th,
                "Điểm chuẩn": score,
                "Năm xét tuyển": year,
                "Ghi chú": ghichu,
                "Môn chính": mon_chinh if mon_chinh else ""
            })

    df_clean = pd.DataFrame(clean_rows)

    print("Đang lọc dữ liệu đủ 7 năm (2019-2025)...")
    df_final = filter_major_full_years(df_clean)

    # Lưu file
    df_final.to_csv(path_output, index=False, encoding="utf-8-sig")
    print(f"Hoàn tất! File lưu tại: {path_output}")

    return df_final

if __name__ == "__main__":
    INPUT_PATH = r"C:\Users\ADMIN\OneDrive - VNU-HCMUS\Documents\GitHub\introduction-to-data-science\data\diem_chuan_all.csv"
    process_diem_chuan(INPUT_PATH)
