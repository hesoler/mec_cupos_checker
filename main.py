import os

from dotenv import load_dotenv

from mec_checker import MECChecker

load_dotenv()

if __name__ == "__main__":
    checker = MECChecker(
        etapa_id=int(os.getenv("ID_ETAPA")),
        headless=False
    )

    try:
        checker.start()
        checker.ensure_login()
        checker.check_tramite()
        checker.process_results()
    finally:
        checker.close()
