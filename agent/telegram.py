"""Telegram 通知。"""
import requests

from .config import env

LIMIT = 4000  # Telegram 單則上限 4096 字


def send(text: str) -> None:
    token, chat_id = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("[Telegram] 沒有設定 TELEGRAM_BOT_TOKEN／TELEGRAM_CHAT_ID，略過")
        return
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text[:LIMIT], "disable_web_page_preview": True},
        timeout=30,
    )
    resp.raise_for_status()
    print("[Telegram] 已送出")
