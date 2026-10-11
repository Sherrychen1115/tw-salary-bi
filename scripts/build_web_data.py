# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""把 data/salary_long.csv 整理成網頁用的 docs/data.json。

用法：
    uv run scripts/build_web_data.py

網頁主題：各行業進入率與退出率的差異，以及它們和薪資的關係。

INDICATORS 是網頁會用到、而且每個行業每一年都有值的指標（進入率、退出率、薪資、工時、人數）。
PARTIAL_INDICATORS 只有部分行業有值（實質經常性薪資、實質總薪資：部門、17 個大類和少數中類），
只收 6 年都有值的行業，網頁端要自己判斷某個行業有沒有這個指標。
完全無資料的 6 個勞動報酬指標不放進去。

自行計算的指標不存在這裡，網頁用下面的數字現算：
流動率 =（進入率 + 退出率）÷ 2、淨進入率 = 進入率 − 退出率、
時薪 = 總薪資 ÷ 總工時、人數指數 = 各年人數 ÷ 109 年人數 × 100。
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
    "entry": "進入率",
    "exit": "退出率",
    "regular": "每人每月經常性薪資",
    "salary": "每人每月總薪資",
    "hours": "總工時",
    "employees": "受僱員工人數",
}
PARTIAL_INDICATORS = {
    "real_regular": "每人每月實質經常性薪資",
    "real_salary": "每人每月實質總薪資",
}
# 這些層級的行業必須全部有值，否則網頁的「實質」切換會壞掉
PARTIAL_REQUIRED_LEVELS = {"大類"}


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

    wanted = {name: key for key, name in {**INDICATORS, **PARTIAL_INDICATORS}.items()}
    units: dict[str, str] = {}
    values: dict[str, dict[str, list]] = {key: {} for key in wanted.values()}
    for r in rows:
        key = wanted.get(r["indicator"])
        if key is None:
            continue
        units[key] = r["unit"]
        if key in PARTIAL_INDICATORS:
            if r["value"] != "":
                series = values[key].setdefault(r["industry"], [None] * len(years))
                series[years.index(int(r["year_roc"]))] = number(r["value"])
            continue
        if r["value"] == "":
            sys.exit(f"{r['indicator']}｜{r['year_roc']}年｜{r['industry']} 無資料，不能當成完整指標")
        series = values[key].setdefault(r["industry"], [None] * len(years))
        series[years.index(int(r["year_roc"]))] = number(r["value"])

    for key in INDICATORS:
        by_industry = values[key]
        if set(by_industry) != set(industries) or any(None in s for s in by_industry.values()):
            sys.exit(f"指標 {INDICATORS[key]} 不是每個行業每一年都有值")
    for key, name in PARTIAL_INDICATORS.items():
        # 只留 6 年都有值的行業
        values[key] = {k: s for k, s in values[key].items() if None not in s}
        required = {i["name"] for i in industries.values() if i["level"] in PARTIAL_REQUIRED_LEVELS}
        if not required <= set(values[key]):
            sys.exit(f"指標 {name} 在 {sorted(required - set(values[key]))} 沒有完整資料")

    data = {
        "meta": {
            "source": "行政院主計總處薪情平臺",
            "period": f"民國 {years[0]}–{years[-1]} 年",
            "downloaded": "2026/10/12",
            "built_from": "data/salary_long.csv",
        },
        "years": years,
        "indicators": {
            **{key: {"name": name, "unit": units[key]} for key, name in INDICATORS.items()},
            **{
                key: {"name": name, "unit": units[key], "partial": True}
                for key, name in PARTIAL_INDICATORS.items()
            },
        },
        "industries": list(industries.values()),
        "values": values,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n"
    )
    print(
        f"完整指標 {len(INDICATORS)} × 年度 {len(years)} × 行業 {len(industries)}"
        f" -> {OUT_PATH.relative_to(ROOT)}（{OUT_PATH.stat().st_size / 1024:.0f} KB）"
    )
    for key, name in PARTIAL_INDICATORS.items():
        print(f"部分指標 {name}：{len(values[key])} 個行業有完整資料")


if __name__ == "__main__":
    main()
