# siti-grants

**台北市 SITI 產業發展獎勵補助申請工具**，讓 Claude Code 幫你搞定從資格確認到計畫書撰寫的全流程。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://claude.ai/code)

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

### 方法二：Clone 後安裝

```bash
git clone https://github.com/<your-username>/siti-grants
cp -r siti-grants/siti-grants ~/.claude/skills/siti-grants
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
- 🔜 **MCP Server**（向量搜尋 + 計畫書 AI 生成，v1.0）

---

## 更新計畫

| 版本 | 內容 | 狀態 |
|-----|------|------|
| **v0.1** | 全計畫規則 + 案例分析 + 台北市問題圖 + 研發模板 + 自查清單 | ✅ 完成 |
| **v0.2** | 創業/品牌模板 + 主題式研發攻略 + 申請策略深度指南 | ✅ 完成 |
| v0.3 | data.taipei 更多資料集整合（商業登記/就業統計）| 🔜 |
| v1.0 | MCP Server（向量搜尋 + 計畫書 AI 生成）| 🔜 |

---

## 授權

MIT License — 自由使用、修改、分發。

---

## 聯絡

發現錯誤或有建議：[GitHub Issues](https://github.com/<your-username>/siti-grants/issues)

> ⚠️ 本工具僅供參考，不保證申請通過。請以 [SITI 官方公告](https://industry-incentive.taipei) 為準。
