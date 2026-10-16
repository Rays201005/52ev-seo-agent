"""共用設定。所有金鑰都從環境變數（GitHub Secrets）讀取，程式碼裡不放任何金鑰。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SITE_URL = "https://52ev.com.tw/"
SITEMAP_URL = SITE_URL + "sitemap.xml"
# Search Console 資源名稱：網域資源用 "sc-domain:52ev.com.tw"，網址前置字元資源用 "https://52ev.com.tw/"
GSC_SITE = os.environ.get("GSC_SITE", "sc-domain:52ev.com.tw")

# 判斷 AI 回答有沒有提到我們
BRAND_TERMS = ["電車玩家", "52ev"]
BRAND_DOMAIN = "52ev.com.tw"

MODEL = "claude-opus-5-5"

QUESTIONS_FILE = ROOT / "questions.yml"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"


def env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None
