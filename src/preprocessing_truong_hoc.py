from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from urllib.parse import quote

import pandas as pd
import requests
from dotenv import load_dotenv


# ==========================
# Cấu hình đường dẫn & .env
# ==========================

# Thư mục src/
SRC_DIR = Path(__file__).resolve().parent
# Thư mục project_root/ (cha của src)
BASE_DIR = SRC_DIR.parent

# .env nằm trong src/.env
ENV_PATH = SRC_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # fallback: nếu sau này bạn chuyển .env ra root
    load_dotenv(BASE_DIR / ".env")

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

if not MAPBOX_TOKEN:
    raise RuntimeError(
        "MAPBOX_TOKEN chưa được set.\n"
        "Hãy tạo file .env trong thư mục src với nội dung:\n"
        "MAPBOX_TOKEN=pk...."
    )


# ==========================
# Hàm gọi Mapbox Geocoding
# ==========================

def geocode_school(
    name: str,
    link: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Gọi Mapbox để lấy (lng, lat) cho một tên trường.
    Trả về (longitude, latitude) hoặc (None, None) nếu không tìm thấy.
    """
    if session is None:
        session = requests.Session()

    # Có thể cải thiện sau bằng cách thêm tỉnh/thành vào query nếu có
    query = f"{name}, Việt Nam"

    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1,
        "language": "vi",
        "country": "VN",
    }

    resp = session.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        return None, None

    # Mapbox: [longitude, latitude]
    coords = features[0]["geometry"]["coordinates"]
    lng, lat = coords[0], coords[1]
    return lng, lat


# ==========================
# Hàm xử lý CSV chung
# ==========================

def add_lat_lng_to_csv(
    input_csv: str,
    output_csv: str,
    name_col: str = "Tên trường",
) -> None:
    """
    Đọc school.csv, thêm cột 'Kinh Độ', 'Vĩ Độ' rồi ghi ra file mới.

    - Kinh Độ = longitude (x)
    - Vĩ Độ   = latitude (y)
    """
    df = pd.read_csv(input_csv)

    if name_col not in df.columns:
        raise ValueError(f"Không tìm thấy cột '{name_col}' trong {input_csv}")

    cache: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
    session = requests.Session()

    for idx, row in df.iterrows():
        school_name = str(row[name_col]).strip()

        if not school_name:
            df.at[idx, "Kinh Độ"] = None
            df.at[idx, "Vĩ Độ"] = None
            continue

        if school_name in cache:
            lng, lat = cache[school_name]
        else:
            try:
                lng, lat = geocode_school(
                    school_name,
                    row.get("Link"),
                    session=session,
                )
            except Exception as e:
                print(f"[ERROR] Không geocode được '{school_name}': {e}")
                lng, lat = None, None

            cache[school_name] = (lng, lat)
            # Tránh spam API (nhất là 300+ trường)
            time.sleep(1)

        # Kinh Độ = longitude, Vĩ Độ = latitude
        df.at[idx, "Kinh Độ"] = lng
        df.at[idx, "Vĩ Độ"] = lat
        print(f"✅ {school_name}: Kinh Độ={lng}, Vĩ Độ={lat}")

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Đã ghi file: {output_csv}")


# ==========================
# Hàm tiện dụng cho file mặc định
# ==========================

def preprocess_school_default() -> None:
    """
    Dùng luôn đường dẫn mặc định:
    input:  project_root/data/school.csv
    output: project_root/data/school_with_coords.csv
    """
    data_dir = BASE_DIR / "data"
    input_path = data_dir / "school.csv"
    output_path = data_dir / "school_with_coords.csv"

    if not input_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file input: {input_path}\n"
            "Hãy chắc rằng file nằm ở: project_root/data/school.csv"
        )

    add_lat_lng_to_csv(str(input_path), str(output_path))


# Cho phép chạy trực tiếp bằng: python -m src.preprocessing_truong_hoc
if __name__ == "__main__":
    preprocess_school_default()
