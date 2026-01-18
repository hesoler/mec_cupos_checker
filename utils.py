import json
import os
from pathlib import Path

import notifier

STATE_FILE = Path("available.json")


def cargar_estado():
    if not STATE_FILE.exists():
        return {"ultima_fecha_notificada": None, "nombre_tramite": None}

    try:
        state = json.loads(STATE_FILE.read_text())
        if not state or not isinstance(state, dict):
            return {"ultima_fecha_notificada": None, "nombre_tramite": None}
        return state
    except json.JSONDecodeError:
        return {"ultima_fecha_notificada": None, "nombre_tramite": None}


def guardar_estado(data):
    STATE_FILE.write_text(
        json.dumps({"ultima_fecha_notificada": data.fecha, "nombre_tramite": data.nombre_tramite}, indent=2)
    )


def validate_env_vars():
    required_vars = [
        "MEC_USER", "MEC_PASSWORD", "ETAPAS_IDS",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHATBOT_IDS", "GROQ_API_KEY"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Validate ETAPAS_IDS
    raw = os.getenv("ETAPAS_IDS")
    if not raw:
        raise ValueError("ETAPAS_IDS cannot be empty")
    try:
        etapas_ids = get_etapa_id_list()
        if not etapas_ids:
            raise ValueError("ETAPAS_IDS must contain at least one valid integer")
    except ValueError as e:
        raise ValueError(f"Invalid ETAPAS_IDS format: {e}")


def get_mec_credentials():
    return {"username": os.getenv("MEC_USER"), "password": os.getenv("MEC_PASSWORD")}


def get_etapa_id_list():
    raw = os.getenv("ETAPAS_IDS")
    return [int(r.strip()) for r in raw.split(",") if r.strip()]


def get_bot_token():
    return os.getenv("TELEGRAM_BOT_TOKEN")


def get_chatbot_id_list():
    raw = os.getenv("TELEGRAM_CHATBOT_IDS", "")
    return [r.strip() for r in raw.split(",") if r.strip()]


def send_notification_message(message):
    bot_token = get_bot_token()
    chatbot_id_list = get_chatbot_id_list()

    for chat_id in chatbot_id_list:
        notifier.send_telegram(
            bot_token,
            chat_id,
            message
        )
