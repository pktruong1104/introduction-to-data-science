# Recommendation System Documentation

## Hệ thống gợi ý ngành học cho thí sinh

**Ngày tạo**: 06/01/2026  
**Author**: Group 05

---

## 1. Problem Statement

### 1.1 Mục tiêu
Gợi ý ngành học phù hợp cho thí sinh dựa trên:
- Điểm thi thực tế
- Điểm chuẩn dự đoán 2024 và điểm chuẩn 2023
- Vị trí địa lý
- Sở thích/xu hướng từ các ngành đã chọn

### 1.2 Yêu cầu
- Gợi ý top K ngành trong khoảng ±1 điểm
- Loại trừ ngành đã chọn
- Ưu tiên theo thứ tự nguyện vọng (NV1 > NV2 > ...)

---

## 2. Data Sources

| File | Mô tả | Sử dụng |
|------|-------|---------|
| `diem_thi_2024_new.csv` | Điểm thi thí sinh | SBD, MA_TINH, điểm từng môn |
| `predictions_2024.csv` | Dự đoán điểm chuẩn | school_code, major_code, predicted |
| `diem_chuan_chuan_hoa.csv` | Điểm chuẩn 2023 | Điểm thực tế năm trước |
| `school_with_coords.csv` | Tọa độ trường | Tính khoảng cách địa lý |
| `province.csv` | Tọa độ tỉnh | Vị trí thí sinh |
| `to_hop.json` | Tổ hợp môn | Tính điểm theo khối |

---

## 3. Methodology

### 3.1 Ranking Formula

```
Score = 0.4 × score_fit + 0.1 × geo + 0.5 × interest
```

| Component | Weight | Mô tả |
|-----------|--------|-------|
| **score_fit** | 40% | Độ khớp điểm với predicted & 2023 |
| **geo** | 10% | Điểm địa lý |
| **interest** | 50% | Similarity với ngành đã chọn |

### 3.2 Score Fit

```
score_fit = 1 - (|điểm_TS - predicted| + |điểm_TS - score_2023|) / 2 / tolerance
```

Chỉ giữ lại ngành có sai lệch ≤ tolerance (default: ±1 điểm).

### 3.3 Geographic Score

**Phân bổ 10% điểm địa lý:**

| Trường hợp | Nhà | NV1 | NV2 | NV3 |
|------------|-----|-----|-----|-----|
| Chưa chọn | 100% | - | - | - |
| 1 NV | 20% | 80% | - | - |
| 2 NV | 20% | 53% | 27% | - |
| 3 NV | 20% | 40% | 27% | 13% |

**Logic:**
- Gần nhà luôn có 20%
- 80% còn lại chia cho các NV đã chọn, ưu tiên theo thứ tự (NV1 > NV2 > ...)

**Distance score:**
```
dist_score = 1 / (1 + distance_km / 100)
```

### 3.4 Interest Similarity

Sử dụng **TF-IDF** trên tên ngành:

1. Vectorize tất cả tên ngành
2. Trung bình vectors ngành đã chọn
3. Cosine similarity với ngành candidate

---

## 4. Implementation

### 4.1 Code Structure

```
src/
└── recsys.py
    │
    ├── load_data()
    │   └── Load tất cả data sources
    │
    ├── RecommendationEngine
    │   ├── _build_tfidf()
    │   ├── _interest_sim()
    │   ├── _calc_geo_score()
    │   └── recommend()
    │
    └── recommend()  ← Shortcut function
```

### 4.2 Usage

```python
from src.recsys import load_data, recommend

# Load data
data = load_data()

# Gợi ý cơ bản
recs = recommend(sbd="1000001", data=data)

# Với prior selections (theo thứ tự NV)
selected = [
    ("QSC", "7340101"),  # NV1
    ("MHN", "7480201"),  # NV2
]
recs = recommend(sbd="1000001", data=data, selected_majors=selected)
```

### 4.3 Parameters

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `sbd` | - | Số báo danh thí sinh |
| `selected_majors` | None | List [(mã_trường, mã_ngành)] theo thứ tự NV |
| `score_tolerance` | 1.0 | Khoảng điểm cho phép (±) |
| `top_k` | 10 | Số lượng gợi ý |
| `verbose` | True | In thông tin debug |

### 4.4 Output

DataFrame với các cột:

| Cột | Mô tả |
|-----|-------|
| `Mã trường` | Mã trường đại học |
| `Tên trường` | Tên đầy đủ |
| `Mã ngành` | Mã ngành |
| `Tên ngành` | Tên ngành |
| `Điểm 2023` | Điểm chuẩn năm trước |
| `Dự đoán` | Điểm dự đoán 2024 |
| `Điểm TS` | Điểm thí sinh (khối cao nhất) |
| `Km` | Khoảng cách từ nhà |
| `Score` | Ranking score |

---

## 5. Example Output

```
Thí sinh: 1000001 | Tỉnh: 01
Đã chọn: 0 ngành | Loại trừ khỏi gợi ý

   Mã trường  Tên trường               Mã ngành  Tên ngành            Score
1       MHN   Trường ĐH Mở Hà Nội      7480201   Công nghệ thông tin  0.448
2       TLA   Trường ĐH Thủy Lợi       TLA112    Kỹ thuật điện        0.442
3       HNM   Trường ĐH Thủ Đô HN      7140201   Giáo dục Mầm non     0.430
```

---

## 6. Limitations & Future Work

### 6.1 Limitations

| Issue | Impact | Possible Solution |
|-------|--------|-------------------|
| TF-IDF đơn giản | Medium | Sentence embeddings |
| Không xét độ hot ngành | Medium | Thêm popularity feature |
| Cố định weights | Low | User-configurable |

### 6.2 Future Improvements

1. **Better embeddings**: sentence-transformers cho similarity
2. **User preferences**: Cho phép set weights
3. **Collaborative filtering**: Dựa trên choices của thí sinh khác
4. **Real-time updates**: Cập nhật khi có thêm nguyện vọng

---

## 7. Files

| File | Location | Mô tả |
|------|----------|-------|
| `recsys.py` | `src/` | Module chính |
| `05_recsys.ipynb` | `notebooks/` | Demo notebook |

---

## References

1. TF-IDF: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
2. Cosine Similarity: https://en.wikipedia.org/wiki/Cosine_similarity
3. Haversine Formula: https://en.wikipedia.org/wiki/Haversine_formula
