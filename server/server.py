"""
siti-grants MCP Server  v1.1
工具：資格判斷 / 語意案例搜尋（Chroma）/ 台北市統計 / 計畫書段落 AI 生成
"""

import asyncio
import json
import os
import re
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

ROOT = Path(__file__).parent.parent
CASES_FILE  = ROOT / "data" / "cases.json"
CHROMA_DIR  = ROOT / "data" / "chroma"

server = Server("siti-grants")

# ---------- lazy singletons ----------

_chroma_collection = None
_cases_cache: list[dict] | None = None


def _get_collection():
    global _chroma_collection
    if _chroma_collection is None and CHROMA_DIR.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            _chroma_collection = client.get_collection("siti_cases")
        except Exception:
            _chroma_collection = None
    return _chroma_collection


def _load_cases() -> list[dict]:
    global _cases_cache
    if _cases_cache is None:
        if CASES_FILE.exists():
            _cases_cache = json.loads(CASES_FILE.read_text(encoding="utf-8"))
        else:
            _cases_cache = []
    return _cases_cache


def _bm25_search(query: str, cases: list[dict], program_filter: str, top_k: int) -> list[dict]:
    """Fallback BM25-lite when Chroma index is unavailable."""
    tokens = re.findall(r"\w+", query.lower())
    def score(c):
        text = " ".join([c.get("計畫名稱",""), c.get("補助計畫",""), c.get("產業別","")]).lower()
        return sum(text.count(t) for t in tokens)
    filtered = [c for c in cases if program_filter == "全部" or program_filter in str(c.get("補助計畫",""))]
    return sorted(filtered, key=score, reverse=True)[:top_k]


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
                    "company_age_months": {"type": "integer", "description": "公司設立至今幾個月"},
                    "has_revenue":         {"type": "boolean", "description": "是否已有實際營業收入"},
                    "investment_amount_twd": {"type": "integer", "description": "近3年獲得投資金額（元），沒有填0"},
                    "primary_need": {
                        "type": "string",
                        "enum": ["技術研發","商業驗證","品牌建立","剛創業","育成機構"],
                    },
                },
                "required": ["company_age_months","has_revenue","investment_amount_twd","primary_need"],
            },
        ),
        types.Tool(
            name="search_approved_cases",
            description=(
                "語意搜尋 2,428 筆歷史通過案例（Chroma 向量搜尋；無 index 時降級為關鍵字搜尋）。"
                "用於了解同類計畫的申請金額與計畫名稱風格。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜尋關鍵字，如「AI 長照」「SaaS B2B」"},
                    "program_type": {
                        "type": "string",
                        "enum": ["全部","創新研發","創業補助","品牌建立","新創拔尖","創新加速"],
                        "default": "全部",
                    },
                    "top_k": {"type": "integer", "default": 5, "description": "回傳幾筆（最多20）"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_taipei_statistics",
            description="取得台北市特定問題領域的開放數據統計，可直接引用於計畫書背景段落。",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "人口老化與長照","少子化與教育","中小企業數位轉型",
                            "健康照護","淨零碳排","交通與移動",
                            "外籍居民","傳統產業","心理健康",
                        ],
                    },
                },
                "required": ["category"],
            },
        ),
        types.Tool(
            name="generate_proposal_section",
            description=(
                "用 Claude AI 生成 SITI 計畫書指定段落。"
                "支援：背景敘事弧 / 創新性三欄對照表 / 效益分析六欄表 / 實施方法摘要。"
                "需設定環境變數 ANTHROPIC_API_KEY。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["背景敘事弧","創新性對照表","效益分析表","實施方法摘要"],
                        "description": "要生成的段落類型",
                    },
                    "company_description": {
                        "type": "string",
                        "description": "公司簡介與產品說明（100-300字）",
                    },
                    "program_type": {
                        "type": "string",
                        "enum": ["創新研發補助","品牌建立補助","創業補助","創新加速補助"],
                        "description": "要申請的補助計畫",
                    },
                    "industry": {
                        "type": "string",
                        "description": "產業別，如「AI SaaS」「醫療健康」「智慧製造」",
                    },
                    "taipei_stats": {
                        "type": "string",
                        "description": "（選填）先用 get_taipei_statistics 取得的統計數字，貼入此欄以強化佐證",
                    },
                },
                "required": ["section","company_description","program_type","industry"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # ── 1. check_eligibility ──────────────────────────────────────────────────
    if name == "check_eligibility":
        age  = arguments["company_age_months"]
        rev  = arguments["has_revenue"]
        inv  = arguments["investment_amount_twd"]
        need = arguments["primary_need"]
        results = []

        if age < 12:
            results.append({"計畫":"創業補助","最高補助":"100萬","建議申請":"滿額100萬","注意":"設立未滿1年才可申請，請盡快送件"})

        if age >= 12:
            if need in ("技術研發","商業驗證"):
                plan   = "創新研發補助" if need == "技術研發" else "創新加速補助"
                amount = "350-450萬" if need == "技術研發" else "250-300萬"
                results.append({"計畫":plan,"最高補助":"500萬" if need=="技術研發" else "300萬","建議申請":amount,"注意":"隨到隨審，全年無截止日"})

            if need == "品牌建立":
                if rev:
                    results.append({"計畫":"品牌建立補助","最高補助":"500萬","建議申請":"300-400萬","注意":"需檢附營業收入佐證，廣告投放費不可申請"})
                else:
                    results.append({"計畫":"品牌建立補助","最高補助":"500萬","建議申請":"⚠️ 目前無營收，先申研發補助，結案後再接品牌補助","注意":"需有營收記錄"})

            if inv >= 5_000_000:
                results.append({"計畫":"新創拔尖補助","最高補助":"1,500萬（三階段）","建議申請":"等梯次公告，需創投推薦書","注意":"若創投不願寫推薦書，先申創新研發補助（不互斥）"})

            results.append({"計畫":"獎勵補貼（可疊加）","最高補助":"租金500萬/薪資500萬","建議申請":"在台北市租辦公室或增員工即可申請，與其他計畫不互斥","注意":"事後申請型"})

        return [types.TextContent(type="text", text=json.dumps({"eligible_programs":results,"tip":"SITI 同一時間只能執行1案，請依時序規劃"}, ensure_ascii=False, indent=2))]

    # ── 2. search_approved_cases ──────────────────────────────────────────────
    elif name == "search_approved_cases":
        query   = arguments.get("query", "")
        prog    = arguments.get("program_type", "全部")
        top_k   = min(int(arguments.get("top_k", 5)), 20)

        collection = _get_collection()
        results_meta: list[dict] = []

        if collection:
            where = None if prog == "全部" else {"補助計畫": {"$contains": prog}}
            try:
                res = collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where,
                    include=["metadatas","distances"],
                )
                results_meta = [
                    {**m, "similarity": round(1 - d, 3)}
                    for m, d in zip(res["metadatas"][0], res["distances"][0])
                ]
                search_mode = "vector (Chroma)"
            except Exception as e:
                results_meta = []
                search_mode = f"vector failed ({e}), falling back to BM25"
        else:
            search_mode = "keyword (BM25, Chroma index not built)"

        if not results_meta:
            cases = _load_cases()
            if not cases:
                return [types.TextContent(type="text", text=json.dumps({
                    "error": "案例資料不存在。請先執行 python scripts/build_cases.py"
                }, ensure_ascii=False))]
            results_meta = [
                {**c, "similarity": None}
                for c in _bm25_search(query, cases, prog, top_k)
            ]

        return [types.TextContent(type="text", text=json.dumps({
            "query": query,
            "search_mode": search_mode,
            "results": results_meta,
        }, ensure_ascii=False, indent=2))]

    # ── 3. get_taipei_statistics ──────────────────────────────────────────────
    elif name == "get_taipei_statistics":
        category = arguments["category"]
        STATS: dict[str, dict] = {
            "人口老化與長照": {
                "key_figures": {"老年人口佔比":"22.4%（超高齡社會）","獨居老人":"約8萬人","長照需求":"約11萬人","服務覆蓋率":"約55%"},
                "proposal_phrases": [
                    "台北市已於114年進入超高齡社會，65歲以上人口佔比達22.4%",
                    "台北市獨居老人逾8萬人，緊急求助回應時間是最關鍵痛點",
                    "台北市長照需求人數約11萬，現行服務覆蓋率僅55%",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=aafb15dc-5508-4091-bd48-a708e60f6698",
            },
            "少子化與教育": {
                "key_figures": {"出生率":"7.7/千人（全國最低）","2023年出生數":"跌破1.5萬","學齡人口年減率":"約1.5-2%/年"},
                "proposal_phrases": [
                    "台北市出生率7.7/千人，為全國最低，教育需求結構正在快速轉變",
                    "台北市學齡人口每年減少約1.5-2%，傳統補教業面臨嚴峻學生來源危機",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=ce5927ec-47fc-4727-9165-0bffdcc45fd0",
            },
            "中小企業數位轉型": {
                "key_figures": {"台北市商業登記":"逾30萬家","中小企業佔比":"97%","基礎數位化完成":"約38%","AI工具導入率":"約12%"},
                "proposal_phrases": [
                    "台北市30萬家商業登記中，中小企業佔97%，但僅38%完成基礎數位化",
                    "台北市中小企業AI工具導入率僅12%，數位轉型缺口達25萬家以上",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=5fdefcca-e0a6-41bc-a520-7c8f067caad3",
            },
            "健康照護": {
                "key_figures": {"慢性病患者比例(40+)":"約45%","精神科候診時間":"3-6個月","每千人醫師數":"3.8（高於全國）"},
                "proposal_phrases": [
                    "台北市40歲以上民眾中，約45%有至少一項慢性病",
                    "台北市精神科門診候診時間平均3-6個月，供需嚴重失衡",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=47109669-1d57-4560-afc4-3b74b31cfb48",
            },
            "淨零碳排": {
                "key_figures": {"建築碳排佔比":"60%","機動車掛牌":"約147萬輛","2030減碳目標":"較2005年-30%","電動機車佔比":"約8%"},
                "proposal_phrases": [
                    "台北市碳排放中，建築物佔60%，是淨零轉型最大攻克目標",
                    "台北市掛牌機動車輛達147萬輛，電動車滲透率仍低於10%",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=c1898379-53b9-4e04-80b6-50506a342311",
            },
            "交通與移動": {
                "key_figures": {"年交通事故":"約8萬件","市區尖峰時速":"16-22km/h","機車日上路":"約147萬輛","YouBike站點":"超過1,800站"},
                "proposal_phrases": [
                    "台北市每年發生約8萬件交通事故，市區尖峰時速僅16-22km/h",
                    "台北市147萬輛機車造成嚴重塞車，主動式智慧交通管理需求急切",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=446eca64-c4f9-4a31-bf0b-db2765c7bb01",
            },
            "外籍居民": {
                "key_figures": {"外籍居民(含移工)":"約13.4萬人","外籍白領":"約3萬人","外籍配偶家庭":"約4.5萬戶","前三大來源國":"越南/印尼/菲律賓"},
                "proposal_phrases": [
                    "台北市外籍居民達13.4萬人，現有政府服務以中文為主，語言障礙是最大痛點",
                    "台北市外籍配偶家庭逾4.5萬戶，子女教育與文化融合服務嚴重不足",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=dc3e7c97-46bb-4e3f-b57c-0cd493048d3e",
            },
            "傳統產業": {
                "key_figures": {"夜市數量":"36個","傳統市場":"62個","傳統零售+餐飲":"約9萬家","現金交易比例":"約70%"},
                "proposal_phrases": [
                    "台北市36個夜市、62個傳統市場，現金交易佔約70%，數位支付滲透率極低",
                    "台北市約9萬家傳統零售與餐飲業，幾乎沒有庫存管理與顧客數據",
                ],
                "data_taipei_url": "https://data.taipei/dataset/detail?id=5fdefcca-e0a6-41bc-a520-7c8f067caad3",
            },
            "心理健康": {
                "key_figures": {"身心障礙者":"約17萬人","精神科候診":"3-6個月","COVID後就診年增":"20%+","心理諮商等候":"公立平均4-8週"},
                "proposal_phrases": [
                    "台北市精神科門診候診時間達3-6個月，心理健康資源嚴重不足",
                    "COVID後台北市心理健康就診人數年增20%以上，服務供給未跟上需求",
                ],
                "note": "data.taipei 目前無直接心理健康統計，建議引用衛生福利部或台北市衛生局年報",
            },
        }
        stat = STATS.get(category)
        if not stat:
            return [types.TextContent(type="text", text=json.dumps({"error":f"未知類別：{category}"}, ensure_ascii=False))]
        return [types.TextContent(type="text", text=json.dumps(stat, ensure_ascii=False, indent=2))]

    # ── 4. generate_proposal_section ──────────────────────────────────────────
    elif name == "generate_proposal_section":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return [types.TextContent(type="text", text=json.dumps({
                "error": "未設定 ANTHROPIC_API_KEY 環境變數。",
                "hint": "export ANTHROPIC_API_KEY=sk-ant-xxxx  # 或在 .env 設定"
            }, ensure_ascii=False))]

        section  = arguments["section"]
        company  = arguments["company_description"]
        program  = arguments["program_type"]
        industry = arguments["industry"]
        stats    = arguments.get("taipei_stats", "")

        PROMPTS = {
            "背景敘事弧": f"""你是台北市 SITI 補助計畫書專家。
請依照「個人觀察 → 痛點 → 國際對標 → 量化市場 → 解決方案」五段結構，
寫一段 400-600 字的計畫書背景段落（申請計畫：{program}）。

公司描述：{company}
產業別：{industry}
可引用的台北市數據：{stats if stats else '（請自行加入適合的數字）'}

要求：
- 主詞用「本計畫」或「本公司」，不用「我們」
- 每個痛點配一個具體數字或實例
- 國際對標舉1-2個真實案例（公司名+成效數字）
- 語氣：政府計畫書正式文體""",

            "創新性對照表": f"""你是台北市 SITI 補助計畫書專家。
請生成一個「創新性三欄對照表」的 Markdown 表格（申請計畫：{program}）。

公司描述：{company}
產業別：{industry}

格式要求：
| 創新項目 | 現況（業界做法）| 本計畫完成後 |
|---------|--------------|------------|
（至少6列，每列描述一個具體創新點）

要求：
- 現況欄要真實描述業界痛點，不能只寫「無」
- 完成後欄要有量化指標（降低X%、提升X倍）
- 涵蓋技術/產品/商業模式三個維度""",

            "效益分析表": f"""你是台北市 SITI 補助計畫書專家。
請生成「效益分析六欄表」（申請計畫：{program}，產業別：{industry}）。

公司描述：{company}

格式要求：
| 效益項目 | 年度目標值 | 佐證來源 |
|---------|----------|---------|

六個必填效益項目（依序）：
1. 帶動產值（仟元）
2. 研發投入（仟元）
3. 吸引投資（仟元）
4. 創造就業（人次）
5. 推出新產品/服務（項）
6. 降低成本效益

要求：
- 金額單位：仟元（不混用萬元）
- 每項必標佐證來源（市場報告/政府統計/公司預估）
- 數字要合理，不能誇大""",

            "實施方法摘要": f"""你是台北市 SITI 補助計畫書專家。
請生成計畫書「實施方法」章節摘要（申請計畫：{program}）。

公司描述：{company}
產業別：{industry}

結構要求（固定順序）：
Phase 0（第1個月）：需求訪談與規格確認
Phase 1（第2-4月）：核心功能雛形
Phase 2（第5-9月）：技術開發與整合
Phase 3（第10-12月）：驗證與試營運

查核點格式：
| 查核點 | 月份 | 可交付產出 | 權重 |
（A/B/C/D 四個查核點，權重合計100%）

要求：
- Phase 描述50-80字
- 查核點產出要具體（不能只寫「完成開發」）
- 前兩個查核點合計 ≥ 50% 權重""",
        }

        prompt_text = PROMPTS.get(section)
        if not prompt_text:
            return [types.TextContent(type="text", text=json.dumps({"error":f"未知段落類型：{section}"}, ensure_ascii=False))]

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt_text}],
            )
            generated = msg.content[0].text
        except Exception as e:
            return [types.TextContent(type="text", text=json.dumps({"error":f"API 呼叫失敗：{e}"}, ensure_ascii=False))]

        return [types.TextContent(type="text", text=json.dumps({
            "section":    section,
            "program":    program,
            "generated":  generated,
            "note": "內容為 AI 生成，送件前請人工確認數字與法規正確性",
        }, ensure_ascii=False, indent=2))]

    return [types.TextContent(type="text", text=json.dumps({"error":f"未知工具：{name}"}, ensure_ascii=False))]


# ---------- entry ----------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="siti-grants",
                server_version="1.1.0",
                capabilities=server.get_capabilities(notification_options=None, experimental_capabilities={}),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
