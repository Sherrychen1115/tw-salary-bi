# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""把 data/salary_long.csv 整理成網頁用的 docs/data.json。

用法：
    uv run scripts/build_web_data.py

只挑網頁會用到、而且每個行業每一年都有值的指標；
完全無資料的 6 個勞動報酬指標和只有部分行業有值的指標都不放進去。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "salary_long.csv"
OUT_PATH = ROOT / "docs" / "data.json"

# 網頁用的 key -> CSV 的 indicator
INDICATORS = {
    "salary": "每人每月總薪資",
    "regular": "每人每月經常性薪資",
    "irregular": "每人每月非經常性薪資",
    "overtime_pay": "每人每月加班費",
    "hours": "總工時",
    "normal_hours": "正常工時",
    "overtime_hours": "加班工時",
    "employees": "受僱員工人數",
}


def number(text: str):
    v = float(text)
    return int(v) if v.is_integer() else v


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    years = sorted({int(r["year_roc"]) for r in rows})
    industries: dict[str, dict] = {}
    for r in rows:
        industries.setdefault(
            r["industry"], {"name": r["industry"], "level": r["level"], "parent": r["parent"]}
        )
    # 每個行業往上找到所屬部門（工業／服務業），網頁用它上色
    for ind in industries.values():
        top = ind
        while top["parent"]:
            top = industries[top["parent"]]
        ind["sector"] = top["name"]

    wanted = {name: key for key, name in INDICATORS.items()}
    units: dict[str, str] = {}
    values: dict[str, dict[str, list]] = {key: {} for key in INDICATORS}
    for r in rows:
        key = wanted.get(r["indicator"])
        if key is None:
            continue
        if r["value"] == "":
            sys.exit(f"{r['indicator']}｜{r['year_roc']}年｜{r['industry']} 無資料，不能當成完整指標")
        units[key] = r["unit"]
        series = values[key].setdefault(r["industry"], [None] * len(years))
        series[years.index(int(r["year_roc"]))] = number(r["value"])

    for key, by_industry in values.items():
        if set(by_industry) != set(industries) or any(None in s for s in by_industry.values()):
            sys.exit(f"指標 {INDICATORS[key]} 不是每個行業每一年都有值")

    data = {
        "meta": {
            "source": "行政院主計總處薪情平臺",
            "period": f"民國 {years[0]}–{years[-1]} 年",
            "downloaded": "2026/10/12",
            "built_from": "data/salary_long.csv",
        },
        "years": years,
        "indicators": {
            key: {"name": name, "unit": units[key]} for key, name in INDICATORS.items()
        },
        "industries": list(industries.values()),
        "values": values,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n"
    )
    print(
        f"指標 {len(values)} × 年度 {len(years)} × 行業 {len(industries)}"
        f" -> {OUT_PATH.relative_to(ROOT)}（{OUT_PATH.stat().st_size / 1024:.0f} KB）"
    )


if __name__ == "__main__":
    main()
