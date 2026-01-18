from dotenv import load_dotenv

from mec_checker import MECChecker
from utils import get_etapa_id_list, validate_env_vars

load_dotenv()


def run_checker():
    validate_env_vars()
    etapas_ids = get_etapa_id_list()

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
