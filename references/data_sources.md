---
purpose: 台北市開放資料 API 清單（與 SITI 補助相關）
last_verified: 2026-06-10
---

# 台北市開放資料 API 清單

> 資料來源：[data.taipei](https://data.taipei/)（臺北市政府資料開放平台）
> 手動瀏覽網址：`https://data.taipei/dataset`

---

## ✅ 已整合的資料集

### SITI 歷史通過案例（核心資料集）

| 項目 | 內容 |
|-----|------|
| **資料集 ID** | `014c6c34-efdb-4aab-9715-50711f14562e` |
| **資料集名稱** | 臺北市產業發展獎勵補助計畫獲獎勵補助廠商基本資料 |
| **資料期間** | 100-114 年（2011-2025）|
| **筆數** | 2,428 筆（截至 2026-02-10）|
| **更新頻率** | 不定期（建議每季抓一次）|

**API 使用方式（PowerShell）**：

```powershell
# 分批取得全部 2,428 筆（每批上限 1,000 筆）
$baseUrl = "https://data.taipei/api/v1/dataset/014c6c34-efdb-4aab-9715-50711f14562e?scope=resourceAquire"
$all = @()
foreach ($offset in @(0, 1000, 2000)) {
    $resp = Invoke-RestMethod -Uri "$baseUrl&limit=1000&offset=$offset" -Method Get
    $all += $resp.result.results
}
Write-Host "共取得 $($all.Count) 筆"
```

**欄位說明**：

| 欄位 | 說明 | 範例 |
|-----|------|------|
| `年度` | 申請獲核年度 | `114` |
| `計畫名稱` | 申請的補助計畫類別 | `創新研發補助` |
| `公司名稱` | 獲補廠商名稱 | `紅點子科技股份有限公司` |
| `補助金額(仟元)` | 核定補助金額（單位：仟元）| `2000` |
| `計畫書名稱` | 計畫書標題 | `大語言模型擬真AI英語家教平台` |
| `行業別` | 統計用行業分類 | `資訊及通訊傳播業` |
| `行政區` | 公司登記行政區 | `大安區` |

**分析成果**：詳見 `references/approved_cases_analysis.md`

---

## 📋 建議後續整合的資料集

以下資料集需手動至 `https://data.taipei/dataset` 搜尋並取得 Dataset ID，才能整合至技能：

| 資料集主題 | 搜尋關鍵字 | 潛在用途 |
|---------|-----------|---------|
| 台北市商業登記統計 | `商業登記` | 各行政區新設公司數量趨勢 → 估算 SITI 競爭激烈程度 |
| 台北市就業人口統計 | `就業` `薪資` | 各產業薪資水準 → 幫助計畫書人事費編列的合理性判斷 |
| 台北市產業統計年報 | `產業統計` | 各行業營業額 → 幫助市場分析數字的本土佐證 |
| 台北市新創生態系報告 | `新創` | 新創數量/募資趨勢 → 新創拔尖補助背景資料 |

---

## 資料更新 SOP

```powershell
# 1. 重新抓取 SITI 案例資料（每季一次）
$baseUrl = "https://data.taipei/api/v1/dataset/014c6c34-efdb-4aab-9715-50711f14562e?scope=resourceAquire"
$all = @()
foreach ($offset in @(0, 1000, 2000)) {
    $resp = Invoke-RestMethod -Uri "$baseUrl&limit=1000&offset=$offset" -Method Get
    $all += $resp.result.results
}

# 2. 匯出 JSON 供分析
$all | ConvertTo-Json -Depth 3 | Out-File "siti_raw_$(Get-Date -Format 'yyyyMMdd').json" -Encoding UTF8

# 3. 更新 approved_cases_analysis.md 中的統計數字
```
