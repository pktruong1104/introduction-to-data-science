from pathlib import Path
import time
import re
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def _start_driver(headless=True, window_size=(1280, 900)):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def _extract_thpt_years_from_dom(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    years = set()
    for tag in soup.find_all(["h3", "strong", "h4", "p"]):
        txt = tag.get_text(" ", strip=True).lower()
        if "điểm chuẩn" in txt and "điểm thi thpt" in txt:
            m = re.search(r"(\d{4})", txt)
            if m:
                years.add(int(m.group(1)))
    return years


def _click_show_more_thpt_until_2019(driver, timeout=5, max_clicks=20):
    seen_years = _extract_thpt_years_from_dom(driver)
    clicks = 0

    def find_candidate_anchors():
        anchors = []
        elems = driver.find_elements(By.TAG_NAME, "a")
        for e in elems:
            try:
                txt = e.text or e.get_attribute("innerText") or ""
            except StaleElementReferenceException:
                continue
            txt_low = txt.strip().lower()
            if "xem thêm" in txt_low and "điểm thi thpt" in txt_low:
                anchors.append(e)
        return anchors

    while clicks < max_clicks:
        if 2019 in seen_years:
            break

        anchors = find_candidate_anchors()
        if not anchors:
            break

        progressed = False
        for a in anchors:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                time.sleep(0.15)
                try:
                    a.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", a)
                clicks += 1
            except StaleElementReferenceException:
                continue

            start = time.time()
            before = set(seen_years)
            while time.time() - start < timeout:
                time.sleep(0.3)
                seen_years = _extract_thpt_years_from_dom(driver)
                if seen_years - before:
                    progressed = True
                    break

            if not progressed:
                time.sleep(0.6)
                seen_years = _extract_thpt_years_from_dom(driver)
                if seen_years == before:
                    pass

            if progressed:
                break

        if not progressed:
            break

    return sorted(list(seen_years), reverse=True)


def _parse_thpt_tables_exact(html, school_code):
    soup = BeautifulSoup(html, "html.parser")
    allowed_years = set(range(2019, 2026))
    results = []

    headings = []
    for h in soup.find_all(["h3", "strong", "h4"]):
        text = h.get_text(" ", strip=True)
        text_low = text.lower()
        if "điểm chuẩn" in text_low and "điểm thi thpt" in text_low:
            headings.append((h, text))

    for heading_tag, heading_text in headings:
        m = re.search(r"(\d{4})", heading_text)
        if not m:
            continue
        year = int(m.group(1))
        if year not in allowed_years:
            continue

        table = heading_tag.find_next("table")
        if table is None:
            container = heading_tag.find_next(lambda t: t.name == "div" and t.find("table"))
            if container:
                table = container.find("table")
        if table is None:
            continue

        ths = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        idx_map = {"stt": None, "ma": None, "ten": None, "tohop": None, "diem": None, "ghichu": None}
        for i, h in enumerate(ths):
            hnorm = h.replace("\xa0", " ").strip()
            if "stt" in hnorm:
                idx_map["stt"] = i
            elif "mã ngành" in hnorm or "ma ngành" in hnorm or "mã ng" in hnorm:
                idx_map["ma"] = i
            elif "tên ngành" in hnorm or hnorm == "tên ngành":
                idx_map["ten"] = i
            elif "tổ hợp" in hnorm:
                idx_map["tohop"] = i
            elif "điểm chuẩn" in hnorm or hnorm == "điểm chuẩn":
                idx_map["diem"] = i
            elif "ghi chú" in hnorm or "ghi chu" in hnorm:
                idx_map["ghichu"] = i

        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            if tr.find_all("th"):
                continue
            tds = tr.find_all("td")
            if not tds:
                continue
            texts = [td.get_text(" ", strip=True) for td in tds]

            def by_key(key, fallback=""):
                idx = idx_map.get(key)
                if idx is not None and idx < len(texts):
                    return texts[idx]
                return fallback

            ma = by_key("ma", "")
            ten = by_key("ten", "")
            tohop = by_key("tohop", "")

            diem = ""
            ghichu = ""

            if idx_map.get("ghichu") is not None and idx_map["ghichu"] < len(tds):
                ghichu = by_key("ghichu", "")
            if idx_map.get("diem") is not None and idx_map["diem"] < len(tds):
                raw_td = tds[idx_map["diem"]]
                cell_text = raw_td.get_text(" ", strip=True)
                if not ghichu:
                    note_tag = raw_td.find(["i", "small", "span"], recursive=True)
                    if note_tag:
                        ghichu = note_tag.get_text(" ", strip=True)
                mnum = re.search(r"[-]?\d+[\.,]?\d*", cell_text)
                if mnum:
                    diem = mnum.group(0)
                else:
                    diem = cell_text.replace(ghichu, "").strip() if ghichu else cell_text
            else:
                if len(texts) >= 5:
                    diem = texts[4]
                    if len(texts) >= 6 and not ghichu:
                        ghichu = texts[5]

            if ghichu and ghichu in diem:
                diem = diem.replace(ghichu, "").strip()

            results.append({
                "Mã ngành": ma,
                "Tên ngành": ten,
                "Tổ hợp môn": tohop,
                "Điểm chuẩn": diem,
                "Ghi chú": ghichu,
                "Mã trường": school_code,
                "Năm xét tuyển": year
            })

    return results


def _norm_tohop(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"\s+", "", s)
    parts = re.split(r"[;,/|]+", s)
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return ";".join(sorted(set(parts)))


def crawl_diem_thpt_from_df(df_schools, start=0, end=None, out_csv=None, headless=True,
                            pause_between=0.8, dedupe=True):
    project_root = Path(__file__).resolve().parent.parent
    default_out = project_root / "data" / "diem_chuan_thpt_2019_2025.csv"
    out_csv = Path(out_csv) if out_csv else default_out
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    subset = df_schools.iloc[start:end].reset_index(drop=True)
    driver = _start_driver(headless=headless)
    collected = []

    existing_keys = set()
    if dedupe and out_csv.exists():
        try:
            df_existing = pd.read_csv(out_csv, dtype=str)
            df_existing = df_existing.fillna("")
            for _, r in df_existing.iterrows():
                key = (
                    (r.get("Mã trường", "") or "").strip(),
                    str(r.get("Năm xét tuyển", "")).strip(),
                    (r.get("Mã ngành", "") or "").strip(),
                    (r.get("Tên ngành", "") or "").strip(),
                    _norm_tohop(r.get("Tổ hợp môn", "")),  # dùng bản chuẩn hóa
                )
                existing_keys.add(key)
            print(f"→ Đã có {len(existing_keys)} dòng trong {out_csv} (sẽ bỏ qua nếu trùng theo 5-field key).")
        except Exception as e:
            print("  ! Không thể đọc file output để dedupe:", e)

    seen_in_run = set()

    try:
        for idx, row in subset.iterrows():
            school_code = row.get("Mã trường") or row.get("Ma truong") or ""
            link = row.get("Link") or row.get("link") or ""
            if not link:
                print(f"[{idx}] Bỏ qua {school_code} — không có Link")
                continue

            print(f"[{idx}] Crawling {school_code} -> {link}")
            try:
                driver.get(link)
            except Exception as e:
                print(f"  ! Lỗi khi load trang: {e}")
                continue

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except TimeoutException:
                print("  ! Timeout khi chờ page body")

            years_seen = _click_show_more_thpt_until_2019(driver, timeout=4, max_clicks=15)
            if years_seen:
                print(f"  🔁 Các năm thấy: {years_seen}")
            if 2019 not in years_seen:
                print("  ⚠️ Chưa thấy năm 2019 — có thể trang không có dữ liệu cũ hoặc click bị chặn.")

            time.sleep(0.4)
            html = driver.page_source
            rows = _parse_thpt_tables_exact(html, school_code)

            if not rows:
                print("  ⚠️ Không tìm thấy bảng 'Điểm thi THPT' 2019–2025 cho trường này.")
                continue

            # dedupe by 5-field key (thêm "Tổ hợp môn")
            new_rows = []
            for r in rows:
                key = (
                    (r.get("Mã trường", "") or "").strip(),
                    str(r.get("Năm xét tuyển", "")).strip(),
                    (r.get("Mã ngành", "") or "").strip(),
                    (r.get("Tên ngành", "") or "").strip(),
                    _norm_tohop(r.get("Tổ hợp môn", "")),
                )
                if dedupe and (key in existing_keys or key in seen_in_run):
                    continue
                new_rows.append(r)
                seen_in_run.add(key)

            if not new_rows:
                print("  (Không có dòng mới sau khi loại trùng)")
                continue

            df_rows = pd.DataFrame(new_rows)
            header = not out_csv.exists()
            try:
                df_rows.to_csv(out_csv, mode="a", index=False, header=header, encoding="utf-8-sig")
            except Exception as e:
                print("  ! Lỗi khi ghi CSV:", e)
                continue

            print(f"  ✅ Lưu {len(df_rows)} dòng vào {out_csv}")
            collected.append(df_rows)
            time.sleep(pause_between)

    finally:
        driver.quit()

    if collected:
        return pd.concat(collected, ignore_index=True)
    else:
        return pd.DataFrame(columns=[
            "Mã ngành", "Tên ngành", "Tổ hợp môn", "Điểm chuẩn", "Ghi chú",
            "Mã trường", "Năm xét tuyển"
        ])
