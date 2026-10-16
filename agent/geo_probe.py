"""GEO 探針：把客戶會問 AI 的問題丟給有上網搜尋能力的 AI，記錄有沒有提到電車玩家、有沒有引用官網。

目前支援：
- claude：Claude＋網路搜尋（只需 ANTHROPIC_API_KEY）
- perplexity：Perplexity Sonar API（需 PERPLEXITY_API_KEY，選用）
沒有金鑰的引擎會自動略過。
"""
from urllib.parse import urlparse

import anthropic
import requests
import yaml

from .config import BRAND_DOMAIN, BRAND_TERMS, MODEL, QUESTIONS_FILE, env

SYSTEM = "你是一般使用者在用的 AI 助理。請用繁體中文、以台灣使用者的角度回答，需要時上網搜尋，並具體推薦店家或網站。"


def load_questions() -> list[dict]:
    data = yaml.safe_load(QUESTIONS_FILE.read_text(encoding="utf-8"))
    out = []
    for group, questions in data.items():
        out.extend({"group": group, "question": q} for q in questions)
    return out


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def score(answer: str, urls: list[str]) -> dict:
    """純規則判斷，不另外花錢叫模型。"""
    domains = sorted({_domain(u) for u in urls if u})
    return {
        "mentioned": any(t.lower() in answer.lower() for t in BRAND_TERMS),
        "cited": any(d == BRAND_DOMAIN or d.endswith("." + BRAND_DOMAIN) for d in domains),
        "cited_domains": domains,
    }


def ask_claude(client: anthropic.Anthropic, question: str) -> tuple[str, list[str]]:
    messages = [{"role": "user", "content": question}]
    tools = [{
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
        "user_location": {"type": "approximate", "country": "TW", "timezone": "Asia/Taipei"},
    }]
    text, urls = [], []
    for _ in range(3):  # pause_turn 最多續跑兩次
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            output_config={"effort": "low"},
            tools=tools,
            messages=messages,
        )
        for block in resp.content:
            if block.type == "text":
                text.append(block.text)
                for c in block.citations or []:
                    if getattr(c, "url", None):
                        urls.append(c.url)
            elif block.type == "web_search_tool_result" and isinstance(block.content, list):
                urls.extend(r.url for r in block.content if getattr(r, "url", None))
        if resp.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": resp.content})
    return "".join(text), urls


def ask_perplexity(key: str, question: str) -> tuple[str, list[str]]:
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "sonar",
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]
    urls = list(data.get("citations") or [])
    urls += [r.get("url") for r in data.get("search_results") or [] if r.get("url")]
    return answer, urls


def collect() -> dict | None:
    engines = {}
    if env("ANTHROPIC_API_KEY"):
        client = anthropic.Anthropic()
        engines["claude"] = lambda q: ask_claude(client, q)
    if env("PERPLEXITY_API_KEY"):
        key = env("PERPLEXITY_API_KEY")
        engines["perplexity"] = lambda q: ask_perplexity(key, q)
    if not engines:
        print("[GEO] 沒有任何 AI 引擎金鑰，略過")
        return None

    questions = load_questions()
    results = []
    for engine, ask in engines.items():
        for item in questions:
            try:
                answer, urls = ask(item["question"])
                results.append({**item, "engine": engine, **score(answer, urls), "answer": answer})
            except Exception as e:  # 單題失敗不影響整份報告
                print(f"[GEO] {engine} 失敗：{item['question']}：{e}")
                results.append({**item, "engine": engine, "error": str(e)})
    ok = [r for r in results if "error" not in r]
    summary = {
        engine: {
            "asked": sum(1 for r in ok if r["engine"] == engine),
            "mentioned": sum(1 for r in ok if r["engine"] == engine and r["mentioned"]),
            "cited": sum(1 for r in ok if r["engine"] == engine and r["cited"]),
        }
        for engine in engines
    }
    print(f"[GEO] {summary}")
    return {"summary": summary, "results": results}
