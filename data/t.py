import pandas as pd
import os

def loc_diem_chuan_thap(duong_dan_file):
    """
    Lọc các dòng dữ liệu từ file CSV có 'Điểm chuẩn' nhỏ hơn 13.0.

    Args:
        duong_dan_file (str): Đường dẫn tới file CSV cần xử lý (ví dụ: 'date/diem_chuan_chuan_hoa.csv').

    Returns:
        pandas.DataFrame: DataFrame chứa các dòng có Điểm chuẩn < 13.0, 
                          hoặc None nếu có lỗi khi đọc file.
    """
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(duong_dan_file):
        print(f"Lỗi: Không tìm thấy file tại đường dẫn: {duong_dan_file}")
        return None

    try:
        # 1. Đọc file CSV vào DataFrame
        df = pd.read_csv(duong_dan_file)

        # 2. Chuyển đổi cột 'Điểm chuẩn' sang dạng số (numeric)
        # errors='coerce' sẽ chuyển đổi các giá trị không phải số thành NaN
        df['Điểm chuẩn'] = pd.to_numeric(df['Điểm chuẩn'], errors='coerce')

        # 3. Lọc DataFrame: chọn các dòng có 'Điểm chuẩn' nhỏ hơn 13.0
        df_ket_qua = df[df['Điểm chuẩn'] < 13.0]

        return df_ket_qua

    except pd.errors.EmptyDataError:
        print("Lỗi: File CSV rỗng.")
        return None
    except Exception as e:
        print(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")
        return None

# --- Ví dụ Sử dụng ---
# Giả định file diem_chuan_chuan_hoa.csv nằm trong thư mục 'date'
duong_dan = 'data/diem_chuan_chuan_hoa.csv'

# LƯU Ý: Để chạy được code này, bạn cần đảm bảo file CSV
# nằm đúng vị trí 'date/diem_chuan_chuan_hoa.csv'
# và chứa dữ liệu phù hợp (bao gồm các cột bạn đã cung cấp).

# Ví dụ nếu file không tồn tại, kết quả sẽ là None:
ket_qua_loc = loc_diem_chuan_thap(duong_dan) 

# Giả sử bạn đang chạy trong môi trường có file dữ liệu
ket_qua_loc = loc_diem_chuan_thap(duong_dan)

if ket_qua_loc is not None and not ket_qua_loc.empty:
    print("Kết quả lọc các ngành có Điểm chuẩn < 13.0:")
    print(ket_qua_loc)
elif ket_qua_loc is not None:
    print("Không tìm thấy ngành nào có Điểm chuẩn nhỏ hơn 13.0.")