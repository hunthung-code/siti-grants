# siti-grants

**台北市 SITI 產業發展獎勵補助申請工具**，讓 Claude Code 幫你搞定從資格確認到計畫書撰寫的全流程。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://claude.ai/code)

![Demo](https://raw.githubusercontent.com/hunthung-code/siti-grants/master/docs/siti_demo.gif)

---

## SITI 是什麼？

[SITI（台北市產業發展局）](https://industry-incentive.taipei) 是台北市政府提供給企業的產業補助計畫窗口。

**最大優勢：全年隨到隨審，沒有截止日。**

| 補助計畫 | 最高金額 | 適合對象 |
|---------|---------|---------|
| 創業補助 | 100 萬 | 設立未滿 1 年 |
| **創新研發補助** | **500 萬** | 設立滿 1 年，有技術創新 |
| 創新加速補助 | 300 萬 | 設立滿 1 年，需商業驗證 |
| **品牌建立補助** | **500 萬** | 設立滿 1 年，有營收 |
| 新創拔尖補助 | 1,500 萬（三階段）| 獲得創投投資 |

補助比例一律 50%（自籌 50%）。

---

## 安裝

### 方法一：直接複製（推薦）

```bash
# Mac / Linux
cp -r siti-grants ~/.claude/skills/siti-grants

# Windows (PowerShell)
Copy-Item -Recurse siti-grants $env:USERPROFILE\.claude\skills\siti-grants
```

### 方法二：npx 一鍵安裝

```bash
npx skills add siegfi/siti-grants
```

### 方法三：Clone 後安裝

```bash
git clone https://github.com/siegfi/siti-grants
cp -r siti-grants ~/.claude/skills/siti-grants
```

---

## 使用方式

安裝後，在 Claude Code 對話中直接問：

```
「我想申請 SITI 補助，公司設立 2 年，主要做 AI SaaS，請問我適合申請哪個？」
「幫我寫 SITI 創新研發補助的計畫書大綱，產品是...」
「我的 SITI 計畫書創新性論述這樣寫對嗎？[貼文字]」
「SITI 有哪些費用不能補助？」
「請幫我做申請前資格確認」
```

---

## MCP Server（進階，v1.1）

讓 Claude Desktop / 任何 MCP client 直接呼叫 SITI 查詢工具。

### 安裝步驟

```bash
# 1. 安裝依賴（含 chromadb + anthropic）
pip install -r server/requirements.txt

# 2. 抓取 2,428 筆通過案例（約 30-60s，需連 data.taipei）
python scripts/build_cases.py

# 3. 建立向量索引（首次約 2-3 分鐘，下載 ~80MB embedding model）
python scripts/build_index.py

# 4. 設定 Anthropic API Key（generate_proposal_section 工具必要）
export ANTHROPIC_API_KEY=sk-ant-...          # Mac/Linux
$env:ANTHROPIC_API_KEY = "sk-ant-..."        # Windows PowerShell
```

### MCP 設定

```json
{
  "mcpServers": {
    "siti-grants": {
      "command": "python",
      "args": ["/path/to/siti-grants/server/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### 可呼叫工具（4 個）

| 工具 | 說明 |
|------|------|
| `check_eligibility` | 輸入公司設立年數 + 特徵，回傳可申請計畫清單與理由 |
| `search_approved_cases` | **向量語意搜尋**通過案例（Chroma，退化為 BM25）|
| `get_taipei_statistics` | 台北市人口/企業數/GDP 統計數字（計畫書引用用）|
| `generate_proposal_section` | **AI 生成**計畫書段落（見下方）|

### `generate_proposal_section` 詳細說明

使用 Claude Haiku 根據你的公司描述自動生成計畫書段落。

**section 類型**：

| 類型 | 輸出內容 |
|------|---------|
| `背景敘事弧` | 觀察 → 痛點 → 國際對標 → 量化市場 → 解方，五段完整敘事 |
| `創新性對照表` | 目標項目 ∣ 現況 ∣ 完成後狀況，≥5 列 Markdown 表格 |
| `效益分析表` | 產值 / 研發 / 投資 / 就業 / 新產品 / 降成本六欄含估算 |
| `實施方法摘要` | Ph0→Ph4 五階段 + 季度查核點（Q1/Q2/Q3/Q4）|

**呼叫範例**：

```
幫我生成 SITI 創新研發補助的「背景敘事弧」段落
公司：AI 聲學監測 SaaS，主要幫工廠做設備預測保養
產業：製造業 / 智慧製造
```

---

## 內容涵蓋

- ✅ **資格快速判斷**：10 分鐘確認適合申請哪個計畫（全計畫覆蓋含育成/獎勵補貼）
- ✅ **各計畫詳細規則**：研發、創業、品牌、新創拔尖、育成、獎勵補貼
- ✅ **歷史通過案例分析**：2,428 筆（100-114 年），含 AI 案例、金額洞察、產業分布
- ✅ **台北市問題全景圖**：9 大真實城市問題 × 技術機會 × 對應補助類別（從問題端找切入點）
- ✅ **計畫書完整模板**：研發 + 創業 + 品牌補助三類 7 章全模板，含金額策略提示
- ✅ **送件前自查清單**：8 關逐項確認，含財務擔保/有薪實習等常漏項
- ✅ **常見地雷清單**：8 大失敗原因與改法
- ✅ **申請策略深度指南**：選計畫 × 金額策略 × 多案時序規劃 × SITI+SBIR 組合
- ✅ **主題式研發攻略**：梯次型計畫監測法 × 72 小時評估 × 備戰策略
- ✅ **MCP Server v1.1**：Chroma 向量語意搜尋（2,428 案例）+ Claude Haiku 計畫書段落 AI 生成

---

## 更新計畫

| 版本 | 內容 | 狀態 |
|-----|------|------|
| **v0.1** | 全計畫規則 + 案例分析 + 台北市問題圖 + 研發模板 + 自查清單 | ✅ 完成 |
| **v0.2** | 創業/品牌模板 + 主題式研發攻略 + 申請策略深度指南 | ✅ 完成 |
| **v0.3** | data.taipei 9 大問題領域 × 16 個資料集 + batch 驗證腳本 | ✅ 完成 |
| **v1.0** | MCP Server skeleton（check_eligibility / search_approved_cases / get_taipei_statistics）+ build_cases.py | ✅ Skeleton 完成 |
| **v1.1** | cases.json 2,428 筆 + Chroma 向量搜尋 + `generate_proposal_section`（Haiku AI 生成四類段落）| ✅ 完成 |
| v1.2 | 多語言 embedding（中文優化）+ 更多 data.taipei 資料集整合 | 🔜 |

---

## 授權

MIT License — 自由使用、修改、分發。

---

## 聯絡

發現錯誤或有建議：[GitHub Issues](https://github.com/siegfi/siti-grants/issues)

> ⚠️ 本工具僅供參考，不保證申請通過。請以 [SITI 官方公告](https://industry-incentive.taipei) 為準。
