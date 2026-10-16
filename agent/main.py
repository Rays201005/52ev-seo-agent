"""每週執行：Search Console → GEO 探針 → 分析週報 → 存檔 → Telegram。

用法：python -m agent.main            # 全部
      python -m agent.main --no-geo   # 不跑 AI 探針（省錢測試用）
"""
import argparse
import json
import os
from datetime import date

from . import analyze, geo_probe, gsc, telegram
from .config import DATA_DIR, REPORTS_DIR


def _save_json(folder, name: str, obj) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def _summary_line(gsc_data: dict | None, geo_data: dict | None) -> str:
    parts = []
    if gsc_data:
        t = gsc_data["totals"]
        parts.append(f"Google 點擊 {t['clicks']}（前期 {t['clicks_prev']}）、曝光 {t['impressions']}（前期 {t['impressions_prev']}）")
    if geo_data:
        for engine, s in geo_data["summary"].items():
            parts.append(f"{engine}：{s['asked']} 題中提到電車玩家 {s['mentioned']} 次、引用官網 {s['cited']} 次")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-geo", action="store_true")
    args = parser.parse_args()

    today = date.today()
    folder = DATA_DIR / today.isoformat()

    gsc_data = gsc.collect(today)
    if gsc_data:
        _save_json(folder, "gsc.json", gsc_data)

    geo_data = None if args.no_geo else geo_probe.collect()
    if geo_data:
        _save_json(folder, "geo.json", geo_data)

    result = analyze.run(today.isoformat(), gsc_data, geo_data)
    report_path = None
    if result["report_markdown"]:
        REPORTS_DIR.mkdir(exist_ok=True)
        report_path = REPORTS_DIR / f"{today.isoformat()}.md"
        report_path.write_text(f"# 電車玩家 SEO／GEO 週報 {today.isoformat()}\n\n{result['report_markdown']}\n", encoding="utf-8")
        print(f"[報告] 已寫入 {report_path}")

    link = ""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if report_path and repo:
        link = f"\n\n完整週報：https://github.com/{repo}/blob/main/reports/{report_path.name}"
    telegram.send(f"📊 電車玩家週報 {today.isoformat()}\n\n{result['telegram_summary']}\n\n{_summary_line(gsc_data, geo_data)}{link}")


if __name__ == "__main__":
    main()
