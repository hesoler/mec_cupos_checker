import smtplib
from email.message import EmailMessage

import requests


def enviar_mail(usuario, password, mensaje):
    msg = EmailMessage()
    msg["Subject"] = "✅ Cupos disponibles – MEC"
    msg["From"] = usuario
    msg["To"] = usuario
    msg.set_content(mensaje)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(usuario, password)
        smtp.send_message(msg)


def enviar_telegram(token, chat_id, mensaje):
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"}

    r = requests.post(url, data=payload, timeout=10)
    r.raise_for_status()
