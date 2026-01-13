import requests
import logging


def send_telegram(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Error sending Telegram notification: {e}")
        raise
