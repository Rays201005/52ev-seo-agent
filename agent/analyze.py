"""策略代理：讀本週數據＋網站現有頁面＋上週報告，寫出繁中週報與下週 SEO 任務。"""
import json

import anthropic
import requests

from .config import MODEL, REPORTS_DIR, SITE_URL, env

SYSTEM = """你是「電車玩家」（52ev.com.tw）的 SEO／GEO 顧問。電車玩家是台灣彰化的特斯拉與電動車事故車收購、維修、二手零件與高壓電池業者，服務全台。
老闆 JR 很忙，報告要結論先講、具體、可執行，用繁體中文與台灣用語。

原則：
- 只根據提供的數據下結論；數據不足時直接說「數據不足」，不要猜。推論要標【推論】。
- 優先順序：直接帶來詢問的主題（事故車收購、大電池、維修）＞零件＞一般知識。
- 任務只挑 3–5 個最值得做的，每個要說明「根據哪個數據」。
- 優先「改既有頁面」（標題、描述、補段落、補 FAQ、內部連結），其次才是新頁面；不要提議和現有頁面重複的新頁面。
- 網站已有嚴格規範：不寫固定報價、不承諾一定收購、不寫高壓系統 DIY、不用 Tesla 原廠 Logo。任務內容要符合這些規範。
- GEO 部分：看 AI 回答時被引用的是哪些網站、有沒有提到電車玩家，說明我們缺什麼內容才會被引用。
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "telegram_summary": {
            "type": "string",
            "description": "給老闆手機看的 5 行以內摘要：本週最重要的變化與最該做的一件事，純文字不用 Markdown 表格",
        },
        "report_markdown": {
            "type": "string",
            "description": "完整週報 Markdown：## 本週結論、## Search Console、## AI 可見度（GEO）、## 上線頁面驗收、## 下週任務（每個任務用 tasks/seo-next.md 的格式：### SEO-XXX 標題、目標、根據的數據、要改的頁面或建議網址、內容重點、內部連結）",
        },
    },
    "required": ["telegram_summary", "report_markdown"],
    "additionalProperties": False,
}


def _fetch(path: str) -> str:
    try:
        resp = requests.get(SITE_URL + path, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        return f"（無法取得 {path}：{e}）"


def _previous_report() -> str:
    reports = sorted(REPORTS_DIR.glob("*.md"))
    return reports[-1].read_text(encoding="utf-8") if reports else "（這是第一份週報）"


def _geo_for_prompt(geo: dict | None) -> dict | None:
    """回答全文太長，只給前 600 字，判斷依據已在欄位裡。"""
    if not geo:
        return None
    return {
        "summary": geo["summary"],
        "results": [{**r, "answer": r.get("answer", "")[:600]} for r in geo["results"]],
    }


def run(today: str, gsc: dict | None, geo: dict | None) -> dict:
    if not env("ANTHROPIC_API_KEY"):
        print("[分析] 沒有 ANTHROPIC_API_KEY，改用無 AI 的簡易報告")
        return {"telegram_summary": "本週數據已收集，但未設定 ANTHROPIC_API_KEY，沒有產生分析。", "report_markdown": ""}

    data = {
        "date": today,
        "search_console": gsc or "（未設定 Search Console）",
        "geo_probe": _geo_for_prompt(geo) or "（未執行 AI 探針）",
    }
    user = (
        f"<網站頁面清單 llms.txt>\n{_fetch('llms.txt')}\n</網站頁面清單 llms.txt>\n\n"
        f"<sitemap>\n{_fetch('sitemap.xml')}\n</sitemap>\n\n"
        f"<上週報告>\n{_previous_report()}\n</上週報告>\n\n"
        f"<本週數據>\n{json.dumps(data, ensure_ascii=False, indent=1)}\n</本週數據>\n\n"
        "請寫本週週報與下週任務。上週報告若有任務，請在「上線頁面驗收」對照相關頁面的數據變化（頁面上線未滿 28 天就註明「觀察期」）。"
    )

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()

    if resp.stop_reason == "refusal":
        raise RuntimeError(f"模型拒絕產生報告：{resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("報告超過長度上限被截斷")
    text = "".join(b.text for b in resp.content if b.type == "text")
    print(f"[分析] 完成，用量 輸入 {resp.usage.input_tokens}／輸出 {resp.usage.output_tokens} tokens")
    return json.loads(text)
