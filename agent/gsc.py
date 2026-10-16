"""Google Search Console：拉最近 28 天與前 28 天的頁面／查詢詞數據。"""
import json
from datetime import date, timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from .config import GSC_SITE, env

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
# GSC 數據大約延遲 2–3 天
LAG_DAYS = 3
WINDOW_DAYS = 28


def _token() -> str:
    info = json.loads(env("GSC_SERVICE_ACCOUNT_JSON"))
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(Request())
    return creds.token


def _query(token: str, start: date, end: date, dimensions: list[str], row_limit: int) -> list[dict]:
    resp = requests.post(
        API.format(site=requests.utils.quote(GSC_SITE, safe="")),
        headers={"Authorization": f"Bearer {token}"},
        json={
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": dimensions,
            "rowLimit": row_limit,
        },
        timeout=60,
    )
    resp.raise_for_status()
    rows = []
    for r in resp.json().get("rows", []):
        row = dict(zip(dimensions, r["keys"]))
        row.update(
            clicks=r["clicks"],
            impressions=r["impressions"],
            ctr=round(r["ctr"], 4),
            position=round(r["position"], 1),
        )
        rows.append(row)
    return rows


def _windows(today: date) -> tuple[tuple[date, date], tuple[date, date]]:
    end = today - timedelta(days=LAG_DAYS)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=WINDOW_DAYS - 1)
    return (start, end), (prev_start, prev_end)


def page_deltas(current: list[dict], previous: list[dict]) -> list[dict]:
    """每頁本期對比上期：點擊、曝光、排名的變化，用來驗收已上線的修改。"""
    prev = {r["page"]: r for r in previous}
    out = []
    for r in current:
        p = prev.get(r["page"])
        out.append({
            "page": r["page"],
            "clicks": r["clicks"],
            "clicks_prev": p["clicks"] if p else 0,
            "impressions": r["impressions"],
            "impressions_prev": p["impressions"] if p else 0,
            "position": r["position"],
            "position_prev": p["position"] if p else None,
        })
    return sorted(out, key=lambda x: x["impressions"], reverse=True)


def opportunities(query_rows: list[dict]) -> dict:
    """兩種最容易見效的機會：排第 8–20 名的詞、曝光高但點擊率低的詞。"""
    striking = [r for r in query_rows if 8 <= r["position"] <= 20 and r["impressions"] >= 20]
    low_ctr = [r for r in query_rows if r["position"] <= 7 and r["impressions"] >= 50 and r["ctr"] < 0.02]
    by_impr = lambda rows: sorted(rows, key=lambda r: r["impressions"], reverse=True)[:30]
    return {"striking_distance": by_impr(striking), "low_ctr": by_impr(low_ctr)}


def collect(today: date) -> dict | None:
    if not env("GSC_SERVICE_ACCOUNT_JSON"):
        print("[GSC] 沒有設定 GSC_SERVICE_ACCOUNT_JSON，略過")
        return None
    token = _token()
    (start, end), (prev_start, prev_end) = _windows(today)
    pages = _query(token, start, end, ["page"], 500)
    pages_prev = _query(token, prev_start, prev_end, ["page"], 500)
    queries = _query(token, start, end, ["query", "page"], 2000)
    print(f"[GSC] {start}～{end}：{len(pages)} 頁、{len(queries)} 組查詢詞")
    return {
        "range": [start.isoformat(), end.isoformat()],
        "range_prev": [prev_start.isoformat(), prev_end.isoformat()],
        "totals": {
            "clicks": sum(r["clicks"] for r in pages),
            "impressions": sum(r["impressions"] for r in pages),
            "clicks_prev": sum(r["clicks"] for r in pages_prev),
            "impressions_prev": sum(r["impressions"] for r in pages_prev),
        },
        "pages": page_deltas(pages, pages_prev),
        "opportunities": opportunities(queries),
        "top_queries": sorted(queries, key=lambda r: r["clicks"], reverse=True)[:50],
    }
