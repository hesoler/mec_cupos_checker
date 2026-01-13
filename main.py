import os

from dotenv import load_dotenv

from mec_checker import MECChecker

load_dotenv()


def validate_env_vars():
    required_vars = [
        "MEC_USER", "MEC_PASSWORD", "ETAPAS_IDS",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GROQ_API_KEY"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Validate ETAPAS_IDS
    raw = os.getenv("ETAPAS_IDS")
    if not raw:
        raise ValueError("ETAPAS_IDS cannot be empty")
    try:
        etapas_ids = get_etapa_id_array()
        if not etapas_ids:
            raise ValueError("ETAPAS_IDS must contain at least one valid integer")
    except ValueError as e:
        raise ValueError(f"Invalid ETAPAS_IDS format: {e}")


def get_etapa_id_array():
    raw = os.getenv("ETAPAS_IDS")
    return [int(r.strip()) for r in raw.split(",") if r.strip()]


def run_checker():
    validate_env_vars()
    etapas_ids = get_etapa_id_array()

    checker = MECChecker(headless=True)

    try:
        checker.start()
        checker.ensure_login()

        for etapa_id in etapas_ids:
            checker.check_tramite(etapa_id)
            checker.process_results()

    finally:
        checker.close()


if __name__ == "__main__":
    run_checker()
