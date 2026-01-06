"""
Hệ thống gợi ý ngành học cho thí sinh.

Usage:
    from src.recsys import load_data, recommend
    
    data = load_data()
    recommendations = recommend(sbd="1000001", data=data, selected_majors=None)
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from math import radians, sin, cos, sqrt, atan2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def load_data() -> dict:
    """Load tất cả dữ liệu cần thiết."""
    diem_thi_2024 = pd.read_csv(os.path.join(DATA_DIR, 'diem_thi_2024_new.csv'), encoding='utf-8-sig')
    diem_thi_2024['SBD'] = diem_thi_2024['SBD'].astype(str)
    diem_thi_2024['MA_TINH'] = diem_thi_2024['MA_TINH'].astype(str).str.zfill(2)
    
    predictions_2024 = pd.read_csv(os.path.join(DATA_DIR, 'predictions_2024.csv'), encoding='utf-8-sig')
    predictions_2024['major_code'] = predictions_2024['major_code'].astype(str)
    
    diem_chuan = pd.read_csv(os.path.join(DATA_DIR, 'diem_chuan_chuan_hoa.csv'), encoding='utf-8-sig')
    diem_chuan_2023 = diem_chuan[diem_chuan['Năm xét tuyển'] == 2023].copy()
    diem_chuan_2023 = diem_chuan_2023[~diem_chuan_2023['Mã ngành'].astype(str).str.contains(r'\*', regex=True)]
    diem_chuan_2023['Mã ngành'] = diem_chuan_2023['Mã ngành'].astype(str)
    
    schools = pd.read_csv(os.path.join(DATA_DIR, 'school_with_coords.csv'), encoding='utf-8-sig')
    schools.columns = ['school_code', 'school_name', 'lat', 'lon']
    
    school_names = pd.read_csv(os.path.join(DATA_DIR, 'school.csv'), encoding='utf-8-sig')
    school_names.columns = ['school_code', 'school_name', 'link']
    
    provinces = pd.read_csv(os.path.join(DATA_DIR, 'province.csv'), encoding='utf-8-sig')
    provinces['MA_TINH'] = provinces['MA_TINH'].astype(str).str.zfill(2)
    
    with open(os.path.join(DATA_DIR, 'to_hop.json'), 'r', encoding='utf-8') as f:
        to_hop = json.load(f)
    
    return {
        'diem_thi_2024': diem_thi_2024,
        'predictions_2024': predictions_2024,
        'diem_chuan_2023': diem_chuan_2023,
        'schools': schools,
        'school_names': school_names,
        'provinces': provinces,
        'to_hop': to_hop
    }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Tính khoảng cách (km) giữa 2 điểm."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _get_coords(code: str, df: pd.DataFrame, code_col: str = 'school_code') -> Optional[Tuple[float, float]]:
    """Lấy tọa độ từ DataFrame."""
    r = df[df[code_col] == code]
    if len(r) == 0:
        return None
    lat_col = 'lat' if 'lat' in r.columns else 'VI_DO'
    lon_col = 'lon' if 'lon' in r.columns else 'KINH_DO'
    return (r.iloc[0][lat_col], r.iloc[0][lon_col])


def _get_candidate_info(sbd: str, data: dict) -> Optional[dict]:
    """Tra cứu thông tin thí sinh."""
    c = data['diem_thi_2024'][data['diem_thi_2024']['SBD'] == str(sbd)]
    if len(c) == 0:
        return None
    r = c.iloc[0]
    return {
        'SBD': r['SBD'], 'MA_TINH': r['MA_TINH'],
        'Toán': r.get('Toán', np.nan), 'Văn': r.get('Văn', np.nan),
        'Ngoại ngữ': r.get('Ngoại ngữ', np.nan), 'Lí': r.get('Lí', np.nan),
        'Hóa': r.get('Hóa', np.nan), 'Sinh': r.get('Sinh', np.nan),
        'Sử': r.get('Sử', np.nan), 'Địa': r.get('Địa', np.nan),
        'GDCD': r.get('GDCD', np.nan)
    }


def _calc_block_scores(info: dict, to_hop: dict) -> dict:
    """Tính điểm theo từng tổ hợp."""
    bs = {}
    for bc, subs in to_hop.items():
        scores = [info.get(s, np.nan) for s in subs]
        if all(not pd.isna(s) for s in scores) and len(scores) == 3:
            bs[bc] = sum(scores)
    return bs


class RecommendationEngine:
    """Hệ thống gợi ý ngành học."""
    
    def __init__(self, data: dict):
        self.data = data
        self._build_tfidf()
    
    def _build_tfidf(self):
        """Build TF-IDF matrix cho tên ngành."""
        self.major_names = self.data['predictions_2024']['major_name'].unique().tolist()
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        self.tfidf_matrix = self.tfidf.fit_transform(self.major_names)
        self.name_to_idx = {n: i for i, n in enumerate(self.major_names)}
    
    def _interest_sim(self, selected_names: List[str], candidate_name: str) -> float:
        """Tính similarity giữa ngành đã chọn và candidate."""
        if not selected_names:
            return 0.0
        vecs = [self.tfidf_matrix[self.name_to_idx[n]].toarray().flatten()
                for n in selected_names if n in self.name_to_idx]
        if not vecs:
            return 0.0
        avg = np.mean(vecs, axis=0).reshape(1, -1)
        if candidate_name in self.name_to_idx:
            cand = self.tfidf_matrix[self.name_to_idx[candidate_name]].toarray()
        else:
            cand = self.tfidf.transform([candidate_name]).toarray()
        return max(0.0, cosine_similarity(avg, cand)[0][0])
    
    def _calc_geo_score(
        self,
        school_code: str,
        home_coords: tuple,
        selected_school_coords: List[tuple]
    ) -> float:
        """
        Tính geo score (0-1).
        
        - Chưa chọn NV: 100% gần nhà
        - Đã chọn NV: 20% nhà + 80% chia cho NV theo priority
        """
        school_coords = _get_coords(school_code, self.data['schools'])
        if not school_coords:
            return 0.0
        
        def dist_score(from_coords, to_coords):
            if not from_coords or not to_coords:
                return 0.0
            d = _haversine(*from_coords, *to_coords)
            return 1 / (1 + d / 100)
        
        home_score = dist_score(home_coords, school_coords)
        
        if not selected_school_coords:
            return home_score
        
        n = len(selected_school_coords)
        weights = [n - i for i in range(n)]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        
        nv_scores = [dist_score(selected_school_coords[i], school_coords) for i in range(n)]
        weighted_nv_score = sum(w * s for w, s in zip(weights, nv_scores))
        
        return 0.2 * home_score + 0.8 * weighted_nv_score
    
    def recommend(
        self,
        sbd: str,
        selected_majors: List[Tuple[str, str]] = None,
        score_tolerance: float = 1.0,
        top_k: int = 10,
        w_score: float = 0.4,
        w_geo: float = 0.1,
        w_interest: float = 0.5,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Gợi ý top K ngành học cho thí sinh.
        
        Args:
            sbd: Số báo danh
            selected_majors: List [(mã_trường, mã_ngành), ...] theo thứ tự NV
            score_tolerance: Khoảng điểm cho phép (±)
            top_k: Số lượng gợi ý
            w_score, w_geo, w_interest: Weights cho ranking
            verbose: In thông tin debug
        
        Returns:
            DataFrame với top K gợi ý
        """
        info = _get_candidate_info(sbd, self.data)
        if not info:
            raise ValueError(f"Không tìm thấy thí sinh: {sbd}")
        
        if verbose:
            print(f"Thí sinh: {sbd} | Tỉnh: {info['MA_TINH']}")
        
        block_scores = _calc_block_scores(info, self.data['to_hop'])
        if not block_scores:
            raise ValueError("Không đủ điểm để tính bất kỳ khối nào.")
        
        prov = self.data['provinces'][self.data['provinces']['MA_TINH'] == info['MA_TINH']]
        home_coords = (prov.iloc[0]['VI_DO'], prov.iloc[0]['KINH_DO']) if len(prov) > 0 else None
        
        selected_names, selected_school_coords, excluded = [], [], set()
        if selected_majors:
            for sc, mc in selected_majors:
                excluded.add((sc, str(mc)))
                sc_coords = _get_coords(sc, self.data['schools'])
                if sc_coords:
                    selected_school_coords.append(sc_coords)
                match = self.data['predictions_2024'][
                    (self.data['predictions_2024']['school_code'] == sc) &
                    (self.data['predictions_2024']['major_code'] == str(mc))
                ]
                if len(match) > 0:
                    selected_names.append(match.iloc[0]['major_name'])
        
        if verbose:
            print(f"Đã chọn: {len(excluded)} ngành | Loại trừ khỏi gợi ý")
        
        preds = self.data['predictions_2024'].copy()
        d23 = self.data['diem_chuan_2023'][['Mã trường', 'Mã ngành', 'Điểm chuẩn', 'Tổ hợp môn']].copy()
        d23.columns = ['school_code', 'major_code', 'score_2023', 'to_hop_mon']
        d23['major_code'] = d23['major_code'].astype(str)
        preds = preds.merge(d23, on=['school_code', 'major_code'], how='left')
        
        results = []
        for _, row in preds.iterrows():
            sc, mc = row['school_code'], row['major_code']
            if (sc, mc) in excluded:
                continue
            
            pred, s23, thm = row['predicted'], row.get('score_2023'), row.get('to_hop_mon', '')
            if pd.isna(pred) or pd.isna(s23) or pd.isna(thm):
                continue
            
            blocks = [b.strip() for b in str(thm).split(';')]
            matches = [block_scores[b] for b in blocks if b in block_scores]
            if not matches:
                continue
            
            cand_score = max(matches)
            if abs(cand_score - pred) > score_tolerance or abs(cand_score - s23) > score_tolerance:
                continue
            
            geo = self._calc_geo_score(sc, home_coords, selected_school_coords)
            interest = self._interest_sim(selected_names, row['major_name'])
            score_fit = 1 - ((abs(cand_score - pred) + abs(cand_score - s23)) / 2 / score_tolerance)
            ranking = w_score * score_fit + w_geo * geo + w_interest * interest
            
            school_coords = _get_coords(sc, self.data['schools'])
            dist_home = _haversine(*home_coords, *school_coords) if home_coords and school_coords else 9999
            
            sn = self.data['school_names'][self.data['school_names']['school_code'] == sc]
            school_name = sn.iloc[0]['school_name'] if len(sn) > 0 else sc
            
            results.append({
                'Mã trường': sc, 'Tên trường': school_name,
                'Mã ngành': mc, 'Tên ngành': row['major_name'],
                'Điểm 2023': round(s23, 2), 'Dự đoán': round(pred, 2),
                'Điểm TS': round(cand_score, 2), 'Km': round(dist_home, 0),
                'Score': round(ranking, 3)
            })
        
        df = pd.DataFrame(results)
        if len(df) == 0:
            if verbose:
                print("Không tìm thấy ngành phù hợp.")
            return pd.DataFrame()
        
        df = df.sort_values('Score', ascending=False).head(top_k).reset_index(drop=True)
        df.index = df.index + 1
        return df


def recommend(
    sbd: str,
    data: dict,
    selected_majors: List[Tuple[str, str]] = None,
    score_tolerance: float = 1.0,
    top_k: int = 10,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Shortcut function để gợi ý ngành học.
    
    Args:
        sbd: Số báo danh
        data: Dict từ load_data()
        selected_majors: List [(mã_trường, mã_ngành), ...] theo thứ tự NV
        score_tolerance: Khoảng điểm cho phép
        top_k: Số lượng gợi ý
        verbose: In thông tin
    
    Returns:
        DataFrame với top K gợi ý
    """
    engine = RecommendationEngine(data)
    return engine.recommend(
        sbd=sbd,
        selected_majors=selected_majors,
        score_tolerance=score_tolerance,
        top_k=top_k,
        verbose=verbose
    )
