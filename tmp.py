import json

# Danh sách mã tỉnh chuẩn
ma_tinh_map = {
    1: 'Hà Nội', 2: 'TP.HCM', 3: 'Hải Phòng', 4: 'Đà Nẵng', 5: 'Hà Giang', 6: 'Cao Bằng',
    7: 'Lai Châu', 8: 'Lào Cai', 9: 'Tuyên Quang', 10: 'Lạng Sơn', 11: 'Bắc Kạn', 12: 'Thái Nguyên',
    13: 'Yên Bái', 14: 'Sơn La', 15: 'Phú Thọ', 16: 'Vĩnh Phúc', 17: 'Quảng Ninh', 18: 'Bắc Giang',
    19: 'Bắc Ninh', 21: 'Hải Dương', 22: 'Hưng Yên', 23: 'Hòa Bình', 24: 'Hà Nam', 25: 'Nam Định',
    26: 'Thái Bình', 27: 'Ninh Bình', 28: 'Thanh Hóa', 29: 'Nghệ An', 30: 'Hà Tĩnh', 31: 'Quảng Bình',
    32: 'Quảng Trị', 33: 'Thừa Thiên - Huế', 34: 'Quảng Nam', 35: 'Quảng Ngãi', 36: 'Kon Tum',
    37: 'Bình Định', 38: 'Gia Lai', 39: 'Phú Yên', 40: 'Đắk Lắk', 41: 'Khánh Hòa', 42: 'Lâm Đồng',
    43: 'Bình Phước', 44: 'Bình Dương', 45: 'Ninh Thuận', 46: 'Tây Ninh', 47: 'Bình Thuận',
    48: 'Đồng Nai', 49: 'Long An', 50: 'Đồng Tháp', 51: 'An Giang', 52: 'Bà Rịa-Vũng Tàu',
    53: 'Tiền Giang', 54: 'Kiên Giang', 55: 'Cần Thơ', 56: 'Bến Tre', 57: 'Vĩnh Long', 58: 'Trà Vinh',
    59: 'Sóc Trăng', 60: 'Bạc Liêu', 61: 'Cà Mau', 62: 'Điện Biên', 63: 'Đắk Nông', 64: 'Hậu Giang'
}

# Lưu ra file json
with open('data/ma_tinh.json', 'w', encoding='utf-8') as f:
    # ensure_ascii=False để giữ tiếng Việt không bị lỗi font
    json.dump(ma_tinh_map, f, ensure_ascii=False, indent=4)

print("Đã tạo file ma_tinh.json thành công!")