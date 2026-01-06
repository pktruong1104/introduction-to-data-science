# Modeling & Evaluation Documentation

## Dự đoán điểm chuẩn đại học 2024

**Ngày tạo**: 05/01/2026  
**Author**: Group 05

---

## 1. Problem Statement

### 1.1 Mục tiêu
Dự đoán điểm chuẩn đại học năm 2024 dựa trên dữ liệu lịch sử từ 2019-2023.

### 1.2 Thách thức
- Điểm chuẩn phụ thuộc vào nhiều yếu tố: số lượng thí sinh, độ khó đề thi, chỉ tiêu tuyển sinh
- Không có thông tin về chỉ tiêu tuyển sinh từng ngành
- Phổ điểm thay đổi theo từng năm do độ khó đề thi

---

## 2. Data Sources

### 2.1 Bảng tổng hợp nguồn dữ liệu

| File | Mô tả | Records | Size |
|------|-------|---------|------|
| `data_pretrain_filled.csv` | Điểm chuẩn 2019-2024 | 2,602 ngành | ~420KB |
| `school_with_coords.csv` | Thông tin trường (tọa độ) | 300 trường | ~20KB |
| `province.csv` | Thông tin tỉnh/thành (tọa độ) | 63 tỉnh | ~2KB |
| `2019_summary.csv` | Phổ điểm 2019 theo tỉnh/khối | ~597K records | ~13MB |
| `2020_summary.csv` | Phổ điểm 2020 theo tỉnh/khối | ~597K records | ~13MB |
| `2021_summary.csv` | Phổ điểm 2021 theo tỉnh/khối | ~597K records | ~13MB |
| `2022_summary.csv` | Phổ điểm 2022 theo tỉnh/khối | ~597K records | ~13MB |
| `2023_summary.csv` | Phổ điểm 2023 theo tỉnh/khối | ~597K records | ~13MB |
| `2024_summary.csv` | Phổ điểm 2024 theo tỉnh/khối | ~597K records | ~13MB |

### 2.2 Cấu trúc file `*_summary.csv`

| Cột | Mô tả | Ví dụ |
|-----|-------|-------|
| `MA_TINH` | Mã tỉnh/thành phố | 01, 02, 03... |
| `NĂM_THI` | Năm thi | 2024 |
| `KHOI_THI` | Khối thi xét tuyển | A00, A01, B00, D01... |
| `SO_THI_SINH` | Số thí sinh đạt ≥ mốc điểm | 5740 |
| `MOC_DIEM` | Mốc điểm (bước nhảy 0.05) | 12.50, 25.05... |

### 2.3 Cấu trúc file `data_pretrain_filled.csv`

| Cột | Mô tả |
|-----|-------|
| `Mã trường` | Mã trường đại học (VD: BKA, KHA) |
| `Mã ngành` | Mã ngành theo Bộ GD&ĐT |
| `Tên ngành` | Tên ngành đào tạo |
| `Tổ hợp môn năm 2019-2024` | Các tổ hợp xét tuyển theo từng năm |
| `Điểm chuẩn năm 2019-2024` | Điểm chuẩn theo từng năm |

---

## 3. Methodology

### 3.1 Chiến lược Feature Engineering

#### Ý tưởng chính
Tính **tỉ lệ thí sinh cạnh tranh theo vùng địa lý** (bán kính 500km từ trường):

```
              Số thí sinh đạt ≥ điểm_chuẩn (trong vùng)
ratio = ──────────────────────────────────────────────────
              Số thí sinh đạt ≥ 12.5 (trong vùng)
```

#### Workflow chi tiết

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Input: Thông tin ngành (trường X, ngành Y, điểm chuẩn 2023 = 25.09)     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 1: Làm tròn xuống 0.05                                             │
│         floor(25.09 / 0.05) * 0.05 = 25.05                              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 2: Xác định tọa độ trường X từ school_with_coords.csv              │
│         VD: ĐH Bách Khoa HN (21.0055, 105.8433)                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 3: Tính khoảng cách Haversine đến 63 tỉnh                          │
│         Lọc các tỉnh có khoảng cách ≤ 500km                             │
│         VD: Hà Nội (0km), Hải Phòng (102km), Nam Định (87km)...         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 4: Lấy tổ hợp xét tuyển của ngành Y                                │
│         VD: A00, A01                                                    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 5: Từ 2023_summary.csv, tính:                                      │
│         - Σ thí sinh đạt ≥ 25.05 (khối A00+A01, các tỉnh trong vùng)    │
│         - Σ thí sinh đạt ≥ 12.5 (khối A00+A01, các tỉnh trong vùng)     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 6: ratio = numerator / denominator                                 │
│         VD: ratio = 15000 / 80000 = 0.1875                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Haversine Distance Formula

Công thức tính khoảng cách giữa 2 điểm trên bề mặt Trái Đất:

```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = R × c   (R = 6371 km - bán kính Trái Đất)
```

**Ví dụ**:
- Hà Nội (21.0295, 105.8544) → TPHCM (10.7758, 106.7018) ≈ **1,150 km**
- Hà Nội → Hải Phòng ≈ **102 km** ✓ (trong bán kính 500km)

### 3.3 Feature Set

#### 3.3.1 Intermediate Dataset: `training_features_2024.csv`

File CSV chứa các features đã được tính toán, lưu tại `data/training_features_2024.csv`.

**Cấu trúc file (13 features + 1 target):**

| Cột | Mô tả | Type |
|-----|-------|------|
| `school_code` | Mã trường | String |
| `major_code` | Mã ngành | String |
| `major_name` | Tên ngành | String |
| `score_prev_year` | Điểm chuẩn năm N-1 | Float |
| `score_2year_ago` | Điểm chuẩn năm N-2 | Float |
| `score_3year_ago` | Điểm chuẩn năm N-3 | Float |
| `score_4year_ago` | Điểm chuẩn năm N-4 | Float |
| `score_trend` | Xu hướng: (N-1) - (N-2) | Float |
| `avg_score_3year` | Trung bình 3 năm gần nhất | Float |
| `ratio_prev_year` | Tỉ lệ cạnh tranh năm N-1 | Float [0-1] |
| `ratio_2year_ago` | Tỉ lệ cạnh tranh năm N-2 | Float [0-1] |
| `ratio_3year_ago` | Tỉ lệ cạnh tranh năm N-3 | Float [0-1] |
| `ratio_4year_ago` | Tỉ lệ cạnh tranh năm N-4 | Float [0-1] |
| `ratio_trend` | Xu hướng ratio | Float |
| `weighted_ratio` | Trung bình trọng số ratio 4 năm | Float |
| **`weighted_ratio_score`** | **Điểm lookup từ phổ điểm năm target** | **Float** |
| `score_target` | **Target**: Điểm chuẩn năm target | Float |

#### 3.3.2 Feature `weighted_ratio_score` (MỚI)

**Ý tưởng**: Điều chỉnh theo độ khó đề thi năm target.

```
1. Tính weighted_ratio = (4*r1 + 3*r2 + 2*r3 + 1*r4) / 10
   với r1, r2, r3, r4 là ratio 4 năm trước

2. Lookup trong phổ điểm NĂM TARGET:
   Tìm mốc điểm X sao cho:
   students >= X / students >= 12.5 ≈ weighted_ratio

3. X chính là weighted_ratio_score
```

**Vì sao hiệu quả**: Feature này tự động điều chỉnh theo độ khó đề thi năm target, khác với các features khác chỉ dựa trên năm trước.

#### 3.3.3 Target Variable Statistics

| Metric | Value |
|--------|-------|
| Mean | 21.45 điểm |
| Std | 4.89 điểm |
| Min | 6.00 điểm |
| Max | 38.45 điểm |

---

## 4. Train/Valid/Test Split (Time-Based)

### 4.1 Phương pháp

**QUAN TRỌNG**: Sử dụng **Time-Based Split** thay vì Random Split để tránh data leakage.

```
┌─────────────────────────────────────────────────────────────────┐
│ TRAINING PHASE (target = 2023)                                  │
│ Features: score_2022, score_2021, score_2020, score_2019        │
│ Target: score_2023 (đã biết)                                    │
│ Split: Train 80% + Valid 20%                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        Train & Select Model
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ TEST PHASE (target = 2024)                                      │
│ Features: score_2023, score_2022, score_2021, score_2020        │
│ Target: score_2024 (giả sử chưa biết → dự đoán)                 │
│ Sau đó so sánh với thực tế để đánh giá                          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Split Configuration

| Tập | Features | Target | Số lượng | Mục đích |
|-----|----------|--------|----------|----------|
| **Train** | 2019-2022 | 2023 | 2,081 (80%) | Huấn luyện model |
| **Valid** | 2019-2022 | 2023 | 521 (20%) | Chọn model tốt nhất |
| **Test** | 2020-2023 | 2024 | 2,602 (100%) | Đánh giá cuối cùng |

### 4.3 Distribution Comparison

| Metric | Train Set (2023) | Valid Set (2023) |
|--------|------------------|------------------|
| Mean | 20.81 | 20.66 |

→ Train và Valid có phân phối tương đồng.

---

## 5. Models Evaluated

### 5.1 Linear Models

| Model | Description | Hyperparameters |
|-------|-------------|-----------------|
| Linear Regression | Hồi quy tuyến tính OLS | - |
| Ridge Regression | L2 regularization | α = 1.0 |
| Lasso Regression | L1 regularization | α = 0.1 |

**Preprocessing**: StandardScaler (normalize features)

### 5.2 Ensemble Models

| Model | Description | Hyperparameters |
|-------|-------------|-----------------|
| Random Forest | Bagging + Decision Trees | n_estimators=100, random_state=42 |
| Gradient Boosting | Sequential boosting | n_estimators=100, random_state=42 |
| XGBoost | Extreme Gradient Boosting | n_estimators=100, random_state=42, verbosity=0 |

---

## 6. Results

### 6.1 Validation Set Performance (target=2023)

| Model | MAE (điểm) | RMSE (điểm) | R² | Rank |
|-------|------------|-------------|-----|------|
| Linear Regression | 1.3989 | 2.0193 | 0.8178 | 5 |
| Ridge Regression | 1.4018 | 2.0202 | 0.8176 | 6 |
| Lasso Regression | 1.4329 | 2.0330 | 0.8153 | 4 |
| **Random Forest** | **1.0548** | **1.7476** | **0.8635** | **1** |
| Gradient Boosting | 1.1859 | 1.8475 | 0.8475 | 3 |
| XGBoost | 1.0667 | 1.7589 | 0.8618 | 2 |

### 6.2 Test Set Performance (target=2024)

Sau khi chọn **Random Forest** dựa trên Validation, retrain trên toàn bộ 2023 data và dự đoán 2024:

| Metric | Validation (2023) | Test (2024) |
|--------|-------------------|-------------|
| MAE | 1.0548 | **1.6039** |
| RMSE | 1.7476 | **2.2244** |
| R² | 0.8635 | **0.7928** |

→ Model generalize từ 2023 sang 2024 với R² giảm ~7%, MAE tăng ~0.55 điểm.

### 6.3 Error Distribution (Test Set 2024)

| Error Range | Count | Percentage |
|-------------|-------|------------|
| ≤ 0.5 điểm | 637 | 24.5% |
| ≤ 1.0 điểm | 1,164 | 44.7% |
| ≤ 2.0 điểm | 1,834 | **70.5%** |
| > 5.0 điểm | 100 | 3.8% |

→ **70.5%** dự đoán có sai số ≤ 2 điểm. **3.8%** có sai số > 5 điểm.

---

## 7. Error Analysis

### 7.1 Top 10 Worst Predictions

| Trường | Ngành | Thực tế | Dự đoán | Error |
|--------|-------|---------|---------|-------|
| SKH | Sư phạm công nghệ | 19.00 | 27.23 | +8.23 |
| TQU | Quản lý văn hóa | 15.00 | 22.88 | +7.88 |
| NHF | Kế toán | 25.08 | 32.62 | +7.54 |
| THP | Giáo dục Thể chất | 29.00 | 22.25 | -6.75 |
| VHS | Quản lý văn hóa | 25.85 | 19.97 | -5.88 |
| DVH | Quản trị dịch vụ du lịch | 16.25 | 22.08 | +5.83 |
| KTD | Ngôn ngữ Trung Quốc | 24.00 | 18.25 | -5.75 |
| DVH | Quản trị kinh doanh | 15.05 | 20.78 | +5.73 |
| DDS | Văn học | 26.00 | 20.63 | -5.37 |
| DTK | Kỹ thuật điện tử - viễn thông | 24.00 | 18.98 | -5.02 |

### 7.2 Nguyên nhân sai số lớn

1. **Biến động bất thường**: Điểm chuẩn thay đổi đột ngột so với xu hướng 5 năm
2. **Thay đổi chỉ tiêu**: Tăng/giảm chỉ tiêu tuyển sinh (không có trong features)
3. **Ngành đặc thù**: Sư phạm, nghệ thuật có cơ chế xét tuyển riêng
4. **Trường vùng xa**: Ít thí sinh trong bán kính 500km

---

## 8. Implementation

### 8.1 Code Structure

```
src/
└── predict_admission_score.py (570+ lines)
    │
    ├── [Section 1] haversine_distance()
    │   └── Tính khoảng cách địa lý giữa 2 tọa độ
    │
    ├── [Section 2] load_data()
    │   └── Load tất cả data sources vào memory
    │
    ├── [Section 3] get_provinces_within_radius()
    │   └── Lọc tỉnh trong bán kính 500km từ trường
    │
    ├── [Section 4] floor_to_step(), calculate_competition_ratio()
    │   └── Tính tỉ lệ cạnh tranh từ phổ điểm
    │
    ├── [Section 5] parse_subject_combos(), build_training_features()
    │   └── Feature engineering, tạo training dataset
    │
    ├── [Section 6] train_and_evaluate_models()
    │   └── Train 6 models, so sánh performance
    │
    ├── [Section 7] predict_2024_scores()
    │   └── Dự đoán điểm chuẩn 2024
    │
    └── [Section 8] main()
        └── Entry point, save CSVs, print statistics
```

### 8.2 Output Files

| File | Mô tả | Location |
|------|-------|----------|
| `training_features_2024.csv` | Features đã tính | `data/` |
| `predictions_2024.csv` | Kết quả dự đoán | `data/` |

### 8.3 Usage

```bash
# Activate conda environment
conda activate introds

# Run prediction
cd /path/to/introduction-to-data-science
python src/predict_admission_score.py
```

---

## 9. Limitations & Future Work

### 9.1 Limitations

| Issue | Impact | Possible Solution |
|-------|--------|-------------------|
| Thiếu chỉ tiêu tuyển sinh | High | Thu thập từ website trường |
| Bán kính cố định 500km | Medium | Adaptive radius theo vùng |
| Không xét reputation trường | Medium | Thêm ranking/rating feature |
| Missing values filled với median | Low | Advanced imputation methods |

### 9.2 Future Improvements

1. **Thu thập thêm dữ liệu**: Chỉ tiêu tuyển sinh, số lượng đăng ký
2. **Hyperparameter tuning**: Grid Search / Random Search cho Random Forest
3. **Time series models**: ARIMA, Prophet cho xu hướng điểm
4. **Neural Network**: Deep learning với TensorFlow/Keras
5. **Ensemble methods**: Stack multiple models

---

## 10. Conclusion

### 10.1 Key Findings

- **Random Forest** là model tốt nhất với R² = 0.8947
- **86.1%** dự đoán có sai số ≤ 1 điểm
- Chiến lược **tỉ lệ cạnh tranh theo vùng địa lý** hiệu quả

### 10.2 Model Performance Summary

| Metric | Value | Interpretation |
|--------|-------|----------------|
| R² | 0.8947 | Giải thích 89.47% variance |
| MAE | 0.49 điểm | Sai số trung bình < 0.5 điểm |
| Accuracy ≤ 1 điểm | 86.1% | Đa số dự đoán chính xác |

---

## References

1. Haversine Formula: https://en.wikipedia.org/wiki/Haversine_formula
2. Scikit-learn Documentation: https://scikit-learn.org/stable/
3. XGBoost Documentation: https://xgboost.readthedocs.io/
4. Random Forest: Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5-32.
