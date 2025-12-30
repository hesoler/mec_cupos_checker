import requests


def enviar_telegram(token, chat_id, mensaje):
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"}

    r = requests.post(url, data=payload, timeout=10)
    r.raise_for_status()
