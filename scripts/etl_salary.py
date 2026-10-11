# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openpyxl>=3.1",
# ]
# ///
"""把薪情平臺匯出的 .xlsx（寬格式）轉成長格式 CSV。

用法：
    uv run scripts/etl_salary.py                 # 讀「行政院主計總處統計資料/」裡的 .xlsx
    uv run scripts/etl_salary.py path/to/x.xlsx  # 指定檔案

輸出：data/salary_long.csv（UTF-8 with BOM）
欄位：indicator, unit, year_roc, year_ad, industry, level, parent, value

原始 xlsx 只讀取、不寫回，不會被修改。
"""

from __future__ import annotations

import csv
import re
import sys
import warnings
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "行政院主計總處統計資料"
OUT_PATH = ROOT / "data" / "salary_long.csv"

FIELDS = ["indicator", "unit", "year_roc", "year_ad", "industry", "level", "parent", "value"]

HEADER_ROWS = 3  # 行業 / 總計 / 統計值
FIRST_DATA_COL = 3  # C 欄起是各行業
MISSING = "-"

# 工作表上的行業名稱沒有縮排或編碼，層級只能靠名稱判斷。
# 以下依「行業統計分類」列出部門與大類；其餘欄位視為前一個大類底下的中類。
SECTORS = ["工業", "服務業"]
DIVISIONS = [
    "礦業及土石採取業",
    "製造業",
    "電力及燃氣供應業",
    "用水供應及污染整治業",
    "營建工程業",
    "批發及零售業",
    "運輸及倉儲業",
    "住宿及餐飲業",
    "出版影音及資通訊業",
    "金融及保險業",
    "不動產業",
    "專業﹑科學及技術服務業",
    "支援服務業",
    "教育業（不含小學以上各級公私立學校等）",
    "醫療保健及社會工作服務業",
    "藝術﹑娛樂及休閒服務業",
    "其他服務業",
]
# 例外：這些欄位是中類底下的小類（餐館 + 其他餐飲業 = 餐飲業）
SUBGROUPS = {
    "餐館": "餐飲業",
    "其他餐飲業": "餐飲業",
}

LEVEL_SECTOR = "部門"
LEVEL_DIVISION = "大類"
LEVEL_GROUP = "中類"
LEVEL_SUBGROUP = "小類"


def find_source(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1])
    files = sorted(p for p in SRC_DIR.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        sys.exit(f"找不到 .xlsx：{SRC_DIR}")
    if len(files) > 1:
        print(f"資料夾內有 {len(files)} 個 .xlsx，使用檔名排序最後一個")
    return files[-1]


def split_unit(raw: str) -> tuple[str, str]:
    """'勞動生產力指數(產量)(民國110年=100)' -> ('勞動生產力指數(產量)', '民國110年=100')"""
    m = re.fullmatch(r"(.+)[(（]([^()（）]*)[)）]", raw.strip())
    if not m:
        return raw.strip(), ""
    return m.group(1).strip(), m.group(2).strip()


def parse_year(raw: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*年\s*", str(raw))
    if not m:
        raise ValueError(f"無法解析年度：{raw!r}")
    roc = int(m.group(1))
    return roc, roc + 1911


def build_hierarchy(industries: list[str]) -> dict[str, tuple[str, str]]:
    """回傳 {行業: (level, parent)}，依欄位順序判斷所屬。"""
    missing = [n for n in SECTORS + DIVISIONS + list(SUBGROUPS) if n not in industries]
    if missing:
        raise ValueError(f"表頭找不到預期的行業名稱（分類可能改版）：{missing}")

    hierarchy: dict[str, tuple[str, str]] = {}
    sector = division = None
    for name in industries:
        if name in SECTORS:
            sector, division = name, None
            hierarchy[name] = (LEVEL_SECTOR, "")
        elif name in DIVISIONS:
            if sector is None:
                raise ValueError(f"大類 {name!r} 前面沒有部門欄位")
            division = name
            hierarchy[name] = (LEVEL_DIVISION, sector)
        elif name in SUBGROUPS:
            parent = SUBGROUPS[name]
            if hierarchy.get(parent, ("", ""))[0] != LEVEL_GROUP:
                raise ValueError(f"小類 {name!r} 的上層 {parent!r} 尚未出現")
            hierarchy[name] = (LEVEL_SUBGROUP, parent)
        else:
            if division is None:
                raise ValueError(f"行業 {name!r} 無法歸到任何大類")
            hierarchy[name] = (LEVEL_GROUP, division)
    return hierarchy


def clean_value(v):
    """'-' 與空白是無資料 -> None；數字原樣保留（整數不帶小數點）。"""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s in ("", MISSING):
            return None
        v = float(s.replace(",", ""))
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def extract(path: Path) -> list[dict]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # 匯出檔沒有預設樣式，openpyxl 會警告
        wb = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = wb.worksheets[0]  # 只讀第一個工作表
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()

    head = rows[:HEADER_ROWS]
    col0 = FIRST_DATA_COL - 1
    industries = [str(v).strip() for v in head[0][col0:] if v not in (None, "")]
    n = len(industries)
    if len(set(industries)) != n:
        raise ValueError("表頭的行業名稱有重複")
    if set(head[1][col0 : col0 + n]) != {"總計"} or set(head[2][col0 : col0 + n]) != {"統計值"}:
        raise ValueError("第 2、3 列表頭不是預期的「總計 / 統計值」")
    hierarchy = build_hierarchy(industries)

    records: list[dict] = []
    indicator_raw = None
    for row in rows[HEADER_ROWS:]:
        a, b = row[0], row[1]
        if isinstance(a, str) and a.strip().startswith("註"):
            break  # 「註:」之後都是附註
        if a not in (None, ""):
            indicator_raw = str(a).strip()  # 合併儲存格：只有第一列有值，往下填滿
        if b in (None, ""):
            continue  # 空白列
        if indicator_raw is None:
            raise ValueError("資料列前面沒有指標名稱")
        indicator, unit = split_unit(indicator_raw)
        year_roc, year_ad = parse_year(b)
        for name, v in zip(industries, row[col0 : col0 + n]):
            level, parent = hierarchy[name]
            value = clean_value(v)
            records.append(
                {
                    "indicator": indicator,
                    "unit": unit,
                    "year_roc": year_roc,
                    "year_ad": year_ad,
                    "industry": name,
                    "level": level,
                    "parent": parent,
                    "value": "" if value is None else value,
                }
            )
    return records


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    src = find_source(sys.argv)
    records = extract(src)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    indicators = {r["indicator"] for r in records}
    years = {r["year_roc"] for r in records}
    industries = {r["industry"] for r in records}
    empty = sum(1 for r in records if r["value"] == "")
    print(f"來源：{src.name}")
    print(
        f"指標 {len(indicators)} × 年度 {len(years)}（民國 {min(years)}–{max(years)}）"
        f" × 行業 {len(industries)} = {len(records)} 列，其中無資料 {empty} 列"
    )
    print(f"輸出：{OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
