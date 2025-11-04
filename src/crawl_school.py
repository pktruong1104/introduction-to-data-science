# src/crawl_school.py
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd

def crawl_school_data(out_path=None):
    # ✅ Đường dẫn tuyệt đối bạn muốn lưu file CSV
    out_path = Path("/home/truong/Documents/introduction-to-data-science/data/school.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ✅ URL nguồn
    base_url = "https://diemthi.tuyensinh247.com"
    url = f"{base_url}/diem-chuan.html"

    # Gửi request và parse HTML
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    # Crawl dữ liệu
    schools = []
    for div in soup.find_all("div", class_="list-schol-box"):
        for a in div.find_all("a", href=True):
            s = a.find("strong")
            if s:
                ma = s.text.strip()
                ten = a.text.replace(ma, "").replace("-", "").strip()
                link = base_url + a["href"]  # ✅ nối link đầy đủ
                schools.append({
                    "Mã trường": ma,
                    "Tên trường": ten,
                    "Link": link
                })

    # Lưu CSV
    df = pd.DataFrame(schools)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"✅ Đã lưu {len(df)} trường vào '{out_path}' (có cả link)")
    return df
