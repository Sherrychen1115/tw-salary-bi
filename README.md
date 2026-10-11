# 東華大學在學與休學人數 BI Demo（Template）

用 AI（Claude Code）把學校公開的統計報表，做成一個可以互動篩選的 BI 網頁，並用 GitHub Pages 對外發佈。

- 資料範圍：國立東華大學 111 學年度上學期 至 114 學年度上學期，共 7 個學期
- 資料性質：公開資料，原始檔與 ETL 後的資料都放在這個 repo，歡迎直接取用

## 課堂流程（90 分鐘）

| 段 | 內容 | 時間 |
|---|---|---|
| [P0](prompts/P0-開始.md) | 用這個 template 建立自己的 repo，啟動 Claude Code | 10 分 |
| [P1](prompts/P1-ETL.md) | 用 AI 做 ETL：把一份 Excel 報表轉成整齊的 CSV，並驗證 | 12 分 |
| [P2](prompts/P2-做出BI網頁.md) | 請 AI 做出互動 BI 網頁 | 35 分 |
| [P3](prompts/P3-發佈.md) | push 到 GitHub，開啟 GitHub Pages | 10 分 |
| [課後練習](prompts/課後練習.md) | 完成課堂內容、用 AI 對 PDF 做 ETL、思考休學比例的分母（不評分） | — |
| [作業](prompts/作業.md) | 自己找資料做 BI 網頁並發佈，由 AI 評分（[評分說明](https://github.com/samsonchen/ai_workshop_assets/tree/main/chapter_2)） | — |

每一段的 prompt 都可以直接複製貼到 Claude Code。

## 目錄

```
東華大學統計資料/        原始檔（學校公告的 XLS 與 PDF，未經修改）
  在學人數統計表/        7 個學期的在學學生人數（.xls）
  休學人數統計表/        7 個學期的休學人數（.pdf）
data/                    ETL 後的標準資料（CSV，UTF-8，可直接用 Excel 開）
  enrollment.csv         在學人數
  leave.csv              休學人數
  dept_mapping.csv       系所對照表
scripts/validate.py      驗證你 ETL 產出的資料是否和標準資料一致
prompts/                 課堂 prompt
docs/                    （你在 P2 做出來的網頁會放在這裡，GitHub Pages 從這裡發佈）
```

## 資料欄位

**data/enrollment.csv**（每列：學期 × 系所 × 學制 × 性別）

| 欄位 | 說明 |
|---|---|
| semester | 學期，例如 `114-1` |
| college | 學院（以 114-1 的組織為準） |
| dept | 系所標準名稱（以 114-1 為準，見 dept_mapping.csv） |
| dept_raw | 報表上的原始系所名稱 |
| degree | 學位別：學士、碩士、博士（碩士在職專班歸入碩士） |
| program_raw | 原始學制：學士班、碩士班、碩士在職專班、博士班 |
| gender | 女、男 |
| count | 在學人數 |

**data/leave.csv**（每列：學期 × 系所 × 學制 × 性別 × 身份類別 × 休學原因；兩個人數都是 0 的列已省略）

| 欄位 | 說明 |
|---|---|
| semester, college, dept, dept_raw, degree, program_raw, gender | 同上 |
| identity | 身份類別：一般生(非原住民族)、原住民族學生、其他類學生 |
| reason | 休學原因（14 種自請休學原因 + 勒令休學的違反校規、其他；勒令休學的「其他」這 7 學期都是 0，所以不會出現） |
| reason_group | 自請休學、勒令休學 |
| new_leave | 學期間休學人數（這學期新辦休學） |
| on_leave_end | 於學期底處於休學狀態之人數 |

**data/dept_mapping.csv**

| 欄位 | 說明 |
|---|---|
| dept | 系所標準名稱 |
| college | 所屬學院 |
| aliases | 過去使用的名稱，以 `;` 分隔 |

## 使用前請注意

- 系所對照（改名、停招後由哪個系承接）是人工判斷，可能有誤。
- 休學比例在網頁上定義為「學期間休學人數 ÷ 在學人數」。分母怎麼選會影響結論，可以自己想想看其他算法。
- 休學人數統計表的上學期資料，在隔年 3 月才填報，所以最新一學期的休學資料會比在學人數晚出現。
- 在學人數不含休學中的學生（依教育部定義）。
