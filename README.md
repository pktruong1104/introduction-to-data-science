# 🎓 Dự đoán Điểm chuẩn Đại học & Gợi ý Nguyện vọng

> **Đồ án môn Nhập môn Khoa học Dữ liệu**

## 👥 Nhóm 5

| MSSV | Họ và Tên |
|------|-----------|
| 23120386 | Phan Khắc Trường |
| 23120403 | Huỳnh Trọng Viên |
| 23120390 | Cao Quốc Tuấn |
| 23120347 | Nguyễn Kim Quốc |

---

## 📋 Giới thiệu

Đồ án tập trung vào hai bài toán chính:

1. **Dự đoán điểm chuẩn đại học 2024** - Sử dụng dữ liệu lịch sử điểm chuẩn (2019-2023) kết hợp với phổ điểm thi THPT theo vùng địa lý để dự đoán điểm chuẩn năm 2024.

2. **Hệ thống gợi ý nguyện vọng** - Gợi ý ngành học phù hợp cho thí sinh dựa trên điểm thi, vị trí địa lý và sở thích cá nhân.

---

## 📁 Cấu trúc thư mục

```
introduction-to-data-science/
├── 📂 data/                          # Dữ liệu
│   ├── diem_thi_*.csv                # Điểm thi THPT 2019-2024
│   ├── diem_chuan_*.csv              # Điểm chuẩn đại học
│   ├── *_summary.csv                 # Phổ điểm theo tỉnh/khối
│   ├── school_with_coords.csv        # Thông tin trường + tọa độ
│   ├── province.csv                  # Thông tin tỉnh/thành
│   ├── predictions_2024.csv          # Kết quả dự đoán 2024
│   └── ...
├── 📂 notebooks/                     # Jupyter Notebooks
│   ├── 01_data_collection.ipynb      # Thu thập dữ liệu
│   ├── 02_data_preprocessing.ipynb   # Tiền xử lý
│   ├── 03_data_exploration_and_visualization.ipynb
│   ├── 04_modeling_and_evaluation.ipynb
│   └── 05_recsys.ipynb               # Hệ thống gợi ý
├── 📂 src/                           # Source code
│   ├── crawl_*.py                    # Scripts crawl dữ liệu
│   ├── preprocessing_*.py            # Scripts tiền xử lý
│   ├── predict_admission_score.py    # Dự đoán điểm chuẩn
│   ├── recsys.py                     # Hệ thống gợi ý
│   └── visualize_*.py                # Scripts visualization
├── 📂 charts/                        # Biểu đồ đã xuất
├── 📂 reports/                       # Tài liệu báo cáo
├── requirements.txt
└── README.md
```

---

## 🚀 Cách chạy

### 1. Cài đặt môi trường

```bash
# Clone repo
git clone <repo-url>
cd introduction-to-data-science

# Tạo virtual environment (khuyến nghị)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. Chạy Notebooks

Mở các notebook theo thứ tự:

```bash
jupyter notebook
```

1. `01_data_collection.ipynb` - Thu thập dữ liệu
2. `02_data_preprocessing.ipynb` - Tiền xử lý dữ liệu
3. `03_data_exploration_and_visualization.ipynb` - Khám phá & trực quan hóa
4. `04_modeling_and_evaluation.ipynb` - Xây dựng mô hình dự đoán
5. `05_recsys.ipynb` - Hệ thống gợi ý nguyện vọng

---

## 🛠️ Tech Stack

- **Python 3.11**
- **pandas, numpy** - Xử lý dữ liệu
- **scikit-learn, XGBoost, TensorFlow** - Machine Learning
- **matplotlib, seaborn** - Visualization
- **Selenium, BeautifulSoup** - Web scraping

---

## 📊 Kết quả

- Dự đoán điểm chuẩn 2024 cho **2,602 ngành** từ **300+ trường đại học**
- Hệ thống gợi ý nguyện vọng dựa trên **điểm thi + vị trí + sở thích**

---

## 📝 License

MIT License © 2026 Group 05
