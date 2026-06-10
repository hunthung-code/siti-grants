"""
siti-grants MCP Server
三個核心工具：資格判斷 / 案例搜尋 / 台北市統計
"""

import asyncio
import json
import re
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

ROOT = Path(__file__).parent.parent
CASES_FILE = ROOT / "data" / "cases.json"

server = Server("siti-grants")


# ---------- helpers ----------

def load_cases() -> list[dict]:
    if CASES_FILE.exists():
        return json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return []


def simple_score(case: dict, query: str) -> int:
    """BM25-lite: count query token hits across key fields."""
    tokens = re.findall(r"\w+", query.lower())
    text = " ".join([
        str(case.get("計畫名稱", "")),
        str(case.get("補助計畫", "")),
        str(case.get("產業別", "")),
    ]).lower()
    return sum(text.count(t) for t in tokens)


# ---------- tools ----------

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="check_eligibility",
            description=(
                "根據公司設立年數、是否有營收、是否有創投投資，判斷可申請哪些 SITI 計畫，"
                "並給出金額建議與注意事項。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company_age_months": {
                        "type": "integer",
                        "description": "公司設立至今幾個月（例：18）",
                    },
                    "has_revenue": {
                        "type": "boolean",
                        "description": "是否已有實際營業收入",
                    },
                    "investment_amount_twd": {
                        "type": "integer",
                        "description": "近 3 年獲得的投資金額（新台幣元，沒有填 0）",
                    },
                    "primary_need": {
                        "type": "string",
                        "enum": ["技術研發", "商業驗證", "品牌建立", "剛創業", "育成機構"],
                        "description": "最主要的補助需求",
                    },
                },
                "required": ["company_age_months", "has_revenue", "investment_amount_twd", "primary_need"],
            },
        ),
        types.Tool(
            name="search_approved_cases",
            description=(
                "在 2,428 筆歷史通過案例中，搜尋與你的產品或技術最相關的案例，"
                "用於了解同類計畫的申請金額、計畫名稱風格。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字，如「AI 長照」「SaaS B2B」「電動車」",
                    },
                    "program_type": {
                        "type": "string",
                        "enum": ["全部", "創新研發", "創業補助", "品牌建立", "新創拔尖", "創新加速"],
                        "description": "限定補助計畫類型（選「全部」不限制）",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "回傳幾筆結果（預設 5，最多 20）",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_taipei_statistics",
            description=(
                "取得台北市特定問題領域的開放數據統計，"
                "可直接引用於計畫書的「背景」或「市場分析」段落。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "人口老化與長照",
                            "少子化與教育",
                            "中小企業數位轉型",
                            "健康照護",
                            "淨零碳排",
                            "交通與移動",
                            "外籍居民",
                            "傳統產業",
                            "心理健康",
                        ],
                        "description": "問題領域類別",
                    },
                },
                "required": ["category"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # ── 1. check_eligibility ──────────────────────────────────────────────────
    if name == "check_eligibility":
        age = arguments["company_age_months"]
        has_rev = arguments["has_revenue"]
        inv = arguments["investment_amount_twd"]
        need = arguments["primary_need"]

        results = []

        if age < 12:
            results.append({
                "計畫": "創業補助",
                "最高補助": "100 萬",
                "建議申請": "滿額 100 萬",
                "注意": "設立未滿 1 年才可申請，請盡快送件",
            })

        if age >= 12:
            if need in ("技術研發", "商業驗證"):
                plan = "創新研發補助" if need == "技術研發" else "創新加速補助"
                amount = "350-450 萬（別保守，平均申請只有 40% 上限）" if need == "技術研發" else "250-300 萬"
                results.append({
                    "計畫": plan,
                    "最高補助": "500 萬" if need == "技術研發" else "300 萬",
                    "建議申請": amount,
                    "注意": "隨到隨審，全年無截止日",
                })

            if need == "品牌建立" and has_rev:
                results.append({
                    "計畫": "品牌建立補助",
                    "最高補助": "500 萬",
                    "建議申請": "300-400 萬",
                    "注意": "需檢附營業收入佐證（附件五），廣告投放費不可申請",
                })
            elif need == "品牌建立" and not has_rev:
                results.append({
                    "計畫": "品牌建立補助",
                    "最高補助": "500 萬",
                    "建議申請": "尚需有營收記錄才可申請",
                    "注意": "⚠️ 目前無營收，先申請研發補助，結案後再接品牌補助",
                })

            if inv >= 5_000_000:
                results.append({
                    "計畫": "新創拔尖補助",
                    "最高補助": "1,500 萬（三階段）",
                    "建議申請": "等梯次公告（不定期），需創投/天使願意出具推薦書",
                    "注意": "若創投不願意寫推薦書，先申請創新研發補助（不互斥）",
                })

        if age >= 12:
            results.append({
                "計畫": "獎勵補貼（加疊）",
                "最高補助": "租金最高 500 萬 / 薪資最高 500 萬",
                "建議申請": "若在台北市租辦公室或新增員工，可同時申請，不互斥",
                "注意": "事後申請型，租了辦公室 / 發了薪資才能申請",
            })

        output = {"eligible_programs": results, "tip": "SITI 同一時間只能執行 1 案，請依時序規劃（詳見 references/application_strategy.md）"}
        return [types.TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]

    # ── 2. search_approved_cases ──────────────────────────────────────────────
    elif name == "search_approved_cases":
        query = arguments.get("query", "")
        program_filter = arguments.get("program_type", "全部")
        top_k = min(int(arguments.get("top_k", 5)), 20)

        cases = load_cases()
        if not cases:
            return [types.TextContent(type="text", text=json.dumps({
                "error": "案例資料檔不存在。請先執行 python scripts/build_cases.py 建立 data/cases.json",
                "hint": "或至 data.taipei API 014c6c34-efdb-4aab-9715-50711f14562e 下載資料"
            }, ensure_ascii=False))]

        if program_filter != "全部":
            cases = [c for c in cases if program_filter in str(c.get("補助計畫", ""))]

        scored = sorted(cases, key=lambda c: simple_score(c, query), reverse=True)
        top = scored[:top_k]

        output = {
            "query": query,
            "total_cases_searched": len(cases),
            "results": [
                {
                    "計畫名稱": c.get("計畫名稱", ""),
                    "補助計畫": c.get("補助計畫", ""),
                    "補助金額_萬元": c.get("補助金額", ""),
                    "年度": c.get("年度", ""),
                    "產業別": c.get("產業別", ""),
                }
                for c in top
            ],
        }
        return [types.TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]

    # ── 3. get_taipei_statistics ──────────────────────────────────────────────
    elif name == "get_taipei_statistics":
        category = arguments["category"]

        STATS: dict[str, dict] = {
            "人口老化與長照": {
                "dataset_ids": ["aafb15dc-5508-4091-bd48-a708e60f6698", "a6394e3f-3514-4542-87bd-de4310a40db3"],
                "key_figures": {
                    "老年人口佔比": "22.4%（超高齡社會門檻 20%）",
                    "獨居老人人數": "約 8 萬人",
                    "長照需求人數": "約 11 萬人（114 年估計）",
                    "長照服務覆蓋率": "約 55%（仍有 45% 未獲服務）",
                },
                "proposal_phrases": [
                    "台北市已於 114 年進入超高齡社會，65 歲以上人口佔比達 22.4%",
                    "台北市獨居老人逾 8 萬人，緊急求助回應時間是最關鍵痛點",
                    "台北市長照需求人數約 11 萬，但現行服務覆蓋率僅 55%",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=aafb15dc-5508-4091-bd48-a708e60f6698",
            },
            "少子化與教育": {
                "dataset_ids": ["ce5927ec-47fc-4727-9165-0bffdcc45fd0"],
                "key_figures": {
                    "出生率": "7.7/千人（全國最低）",
                    "2023 年出生數": "跌破 1.5 萬（歷史低點）",
                    "學齡人口年減率": "約 1.5-2%/年",
                },
                "proposal_phrases": [
                    "台北市出生率 7.7/千人，為全國最低，教育需求結構正在快速轉變",
                    "台北市學齡人口每年減少約 1.5-2%，傳統補教業面臨嚴峻的學生來源危機",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=ce5927ec-47fc-4727-9165-0bffdcc45fd0",
            },
            "中小企業數位轉型": {
                "dataset_ids": ["5fdefcca-e0a6-41bc-a520-7c8f067caad3", "18f45255-8b16-4e6d-9a77-e48af4e497cd"],
                "key_figures": {
                    "台北市商業登記總數": "逾 30 萬家",
                    "中小企業佔比": "97%",
                    "已完成基礎數位化": "約 38%（113 年調查）",
                    "AI 工具導入率": "約 12%",
                },
                "proposal_phrases": [
                    "台北市 30 萬家商業登記中，中小企業佔 97%，但僅 38% 完成基礎數位化",
                    "台北市中小企業 AI 工具導入率僅 12%，數位轉型缺口達 25 萬家以上",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=5fdefcca-e0a6-41bc-a520-7c8f067caad3",
            },
            "健康照護": {
                "dataset_ids": ["47109669-1d57-4560-afc4-3b74b31cfb48"],
                "key_figures": {
                    "慢性病患者比例（40+歲）": "約 45%",
                    "精神科候診時間": "平均 3-6 個月",
                    "每千人醫師數": "台北市約 3.8（高於全國均值）",
                },
                "proposal_phrases": [
                    "台北市 40 歲以上民眾中，約 45% 有至少一項慢性病",
                    "台北市精神科門診候診時間平均 3-6 個月，供需嚴重失衡",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=47109669-1d57-4560-afc4-3b74b31cfb48",
            },
            "淨零碳排": {
                "dataset_ids": ["c1898379-53b9-4e04-80b6-50506a342311", "78cd7f31-3f87-4b2f-acd3-c887305d4c37"],
                "key_figures": {
                    "建築物碳排放佔比": "60%（最大排放源）",
                    "機動車輛掛牌數": "約 147 萬輛",
                    "2030 減碳目標": "較 2005 年減量 30%",
                    "電動機車佔比": "約 8%（113 年）",
                },
                "proposal_phrases": [
                    "台北市碳排放中，建築物佔 60%，是淨零轉型最大的攻克目標",
                    "台北市掛牌機動車輛達 147 萬輛，電動車滲透率仍低於 10%",
                    "台北市設定 2030 年減碳 30% 目標，科技解決方案需求迫切",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=c1898379-53b9-4e04-80b6-50506a342311",
            },
            "交通與移動": {
                "dataset_ids": ["446eca64-c4f9-4a31-bf0b-db2765c7bb01", "e57afe7f-3c9e-4f31-9208-eed859a92600"],
                "key_figures": {
                    "年交通事故件數": "約 8 萬件（財損/傷亡合計）",
                    "市區尖峰平均時速": "16-22 km/h",
                    "機車日上路量": "約 147 萬輛",
                    "YouBike 站點數": "超過 1,800 站（114 年）",
                },
                "proposal_phrases": [
                    "台北市每年發生約 8 萬件交通事故，市區尖峰時速僅 16-22 km/h",
                    "台北市 147 萬輛機車造成嚴重塞車與碳排放問題，主動式智慧交通管理需求急切",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=446eca64-c4f9-4a31-bf0b-db2765c7bb01",
            },
            "外籍居民": {
                "dataset_ids": ["dc3e7c97-46bb-4e3f-b57c-0cd493048d3e"],
                "key_figures": {
                    "外籍居民（含移工）": "約 13.4 萬人",
                    "外籍白領工作者": "約 3 萬人",
                    "外籍配偶家庭": "約 4.5 萬戶",
                    "前三大來源國": "越南、印尼、菲律賓",
                },
                "proposal_phrases": [
                    "台北市外籍居民達 13.4 萬人，現有政府服務以中文為主，語言障礙是最大痛點",
                    "台北市外籍配偶家庭逾 4.5 萬戶，子女教育與文化融合服務嚴重不足",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=dc3e7c97-46bb-4e3f-b57c-0cd493048d3e",
            },
            "傳統產業": {
                "dataset_ids": ["5fdefcca-e0a6-41bc-a520-7c8f067caad3"],
                "key_figures": {
                    "夜市數量": "36 個（觀光夜市 5 個）",
                    "傳統市場數量": "62 個（公有 43 個）",
                    "傳統零售+餐飲家數": "約 9 萬家",
                    "現金交易比例": "約 70%（無收銀系統）",
                },
                "proposal_phrases": [
                    "台北市 36 個夜市、62 個傳統市場，現金交易佔約 70%，數位支付滲透率極低",
                    "台北市約 9 萬家傳統零售與餐飲業，幾乎沒有庫存管理與顧客數據",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=5fdefcca-e0a6-41bc-a520-7c8f067caad3",
            },
            "心理健康": {
                "dataset_ids": [],
                "key_figures": {
                    "身心障礙者人數": "約 17 萬人",
                    "精神科候診時間": "平均 3-6 個月",
                    "COVID 後就診年增率": "20%+",
                    "心理諮商等候時間": "公立資源平均等候 4-8 週",
                },
                "proposal_phrases": [
                    "台北市精神科門診候診時間達 3-6 個月，心理健康資源嚴重不足",
                    "COVID 後台北市心理健康就診人數年增 20% 以上，但服務供給未跟上需求",
                ],
                "note": "data.taipei 目前無直接心理健康統計，建議引用衛生福利部或台北市衛生局年報",
            },
        }

        stat = STATS.get(category, {})
        if not stat:
            return [types.TextContent(type="text", text=json.dumps({"error": f"未知類別：{category}"}, ensure_ascii=False))]

        return [types.TextContent(type="text", text=json.dumps(stat, ensure_ascii=False, indent=2))]

    return [types.TextContent(type="text", text=json.dumps({"error": f"未知工具：{name}"}, ensure_ascii=False))]


# ---------- entry ----------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="siti-grants",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
