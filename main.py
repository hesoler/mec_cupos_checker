import os

from dotenv import load_dotenv

from mec_checker import MECChecker

load_dotenv()

if __name__ == "__main__":
    # Parsing etapas IDs from environment variable
    raw = os.getenv("ETAPAS_IDS")
    etapas_ids = [int(r.strip()) for r in raw.split(",") if r.strip()]

    checker = MECChecker(
        headless=True
    )

    try:
        checker.start()
        checker.ensure_login()

        for etapa_id in etapas_ids:
            checker.check_tramite(etapa_id)

        checker.process_results()
    finally:
        checker.close()
