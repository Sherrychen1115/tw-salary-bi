# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""
把你用 AI 做 ETL 產出的 114-1 資料，和 data/ 裡的標準資料比對。

用法：
  uv run scripts/validate.py enrollment work/enrollment_114-1.csv   # 課堂 P1：在學人數
  uv run scripts/validate.py leave      work/leave_114-1.csv        # 延伸：休學人數 PDF
"""
import re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SEM = "114-1"
strip = lambda s: re.sub(r"[（(].*?[)）]", "", str(s)).strip()

SPEC = {
    "enrollment": dict(std="enrollment.csv", need=["college", "dept_raw", "program_raw", "gender", "count"],
                       values=["count"], keys=["gender", "program_raw", "college", "dept_raw"]),
    "leave": dict(std="leave.csv", need=["dept_raw", "program_raw", "gender", "reason", "new_leave", "on_leave_end"],
                  values=["new_leave", "on_leave_end"], keys=["gender", "program_raw", "reason", "dept_raw"]),
}

def compare(mine, std, key, values):
    a = mine.groupby(key)[values].sum()
    b = std.groupby(key)[values].sum()
    j = a.join(b, how="outer", lsuffix="_你的", rsuffix="_標準").fillna(0).astype(int)
    bad = j[[any(j.loc[i, f"{v}_你的"] != j.loc[i, f"{v}_標準"] for v in values) for i in j.index]]
    return bad

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in SPEC:
        print(__doc__); sys.exit(2)
    kind, path = sys.argv[1], Path(sys.argv[2])
    spec = SPEC[kind]
    mine = pd.read_csv(path, encoding="utf-8-sig")
    miss = [c for c in spec["need"] if c not in mine.columns]
    if miss:
        print(f"❌ 你的檔案缺少欄位：{', '.join(miss)}（需要：{', '.join(spec['need'])}）"); sys.exit(1)
    std = pd.read_csv(ROOT / "data" / spec["std"], encoding="utf-8-sig")
    std = std[std.semester == SEM]
    for df in (mine, std):
        df["dept_raw"] = df["dept_raw"].map(strip)
        if "college" in df:
            df["college"] = df["college"].map(strip)
        if "reason" in df:
            df["reason"] = df["reason"].map(lambda s: re.sub(r"[、，,\s]", "", str(s)))

    ok = True
    for v in spec["values"]:
        m, s = int(mine[v].sum()), int(std[v].sum())
        print(f"{'✅' if m == s else '❌'} {v} 總數：你的 {m}，標準 {s}")
        ok &= m == s
    for k in spec["keys"]:
        bad = compare(mine, std, k, spec["values"])
        if bad.empty:
            print(f"✅ 依 {k} 分組加總：全部相符")
        else:
            ok = False
            print(f"❌ 依 {k} 分組加總：{len(bad)} 項不符（列出前 10 項）")
            print(bad.head(10).to_string())
    print("\n🎉 全部通過！可以直接用 data/ 裡 7 個學期的完整資料進入下一步。" if ok
          else "\n⚠️ 有差異。把上面的訊息貼給 Claude，請它找出原因；時間不夠就直接用 data/ 的標準資料繼續。")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
