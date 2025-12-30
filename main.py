import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from api import crear_session, consultar_disponibilidades, cookies_validas
from auth import cargar_cookies
from notifier import enviar_telegram
from utils import obtener_tramite_ultima_fecha, cargar_estado, guardar_estado

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

MAX_REINTENTOS = 3


# DEVUELVE UNA LISTA DE ENTEROS CON LOS ID DE RECURSOS A CONSULTAR
def obtener_recursos_env():
    raw = os.getenv("ID_RECURSOS", "")
    return [int(r.strip()) for r in raw.split(",") if r.strip()]


def manejar_cookies():
    cookies = cargar_cookies(os.getenv("MEC_USER"), os.getenv("MEC_PASSWORD"))
    if not cookies:
        raise RuntimeError("❌ Ocurrió un error al cargar las cookies.")
    else:
        session = crear_session(cookies)
        if not cookies_validas(session, int(os.getenv("CHECK_TIMEOUT"))):
            logging.info("❌ Cookies expiradas. Autenticando de nuevo...")
            Path("cookies.json").unlink(missing_ok=True)
            cookies = cargar_cookies(os.getenv("MEC_USER"), os.getenv("MEC_PASSWORD"))
            session = crear_session(cookies)

    return session


def procesar_disponibilidades(session, estado, recurso: int):
    nombre_tramite = estado.get("nombre_tramite")
    id_agenda = int(os.getenv("ID_AGENDA"))
    check_timeout = int(os.getenv("CHECK_TIMEOUT"))
    token = str(os.getenv("TOKEN_DISPONIBILIDADES"))

    data = consultar_disponibilidades(
        session, token, recurso, id_agenda, check_timeout
    )

    lista_datos_tramites = obtener_tramite_ultima_fecha(data)

    if lista_datos_tramites and lista_datos_tramites != estado["ultima_fecha_notificada"]:
        mensaje = (
            f"✅ *Cupos disponibles*\n\n"
            f"🧾 Trámite: *{nombre_tramite or 'Desconocido'}*\n"
            f"📍 Recurso: `{os.getenv('ID_RECURSO')}`\n"
            f"📅 Fecha más próxima: *{lista_datos_tramites}*\n\n"
            f"Ingresá al sistema para reservar."
        )

        enviar_telegram(
            os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"), mensaje
        )
        guardar_estado(lista_datos_tramites)
        logging.info(f"Cupos detectados para {recurso}: {lista_datos_tramites}")
    elif lista_datos_tramites:
        logging.info(f"Cupos ya notificados previamente para {recurso}")
    else:
        logging.info(f"No hay cupos disponibles para {recurso}")


def main():
    estado = cargar_estado()
    try:
        session = manejar_cookies()
        recursos = obtener_recursos_env()
        for recurso in recursos:
            try:
                procesar_disponibilidades(session, estado, recurso)
            except Exception as e:
                logging.warning(f"Error procesando recurso {recurso}: {e}")
        return
    except Exception as e:
        logging.warning(f"Intento fallido: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
