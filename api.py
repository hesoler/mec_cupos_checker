import json
import logging
from pathlib import Path

import requests

API_URL = "https://bpmgob.mec.gub.uy/etapas/agenda_sae_api_disponibilidades"
CA_BUNDLE = Path("mec_chain.pem")


def crear_session(cookies):
    session = requests.Session()

    # 🔐 USAR CA DEL MEC
    session.verify = str(CA_BUNDLE)

    # Agregar headers para simular navegador
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://bpmgob.mec.gub.uy/',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
    })

    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    return session


def consultar_disponibilidades(session, id_recurso, timeout):
    payload = {
        "method": "POST",
        "url": "https://sae.mec.gub.uy/sae-admin/rest/consultas/disponibilidades_por_recurso",
        "id_empresa": 9,
        "id_agenda": 7,
        "id_recurso": id_recurso,
        "idioma": "es",
    }

    r = session.post(API_URL, data=payload, timeout=timeout)
    r.raise_for_status()
    try:
        return r.json()
    except json.JSONDecodeError as e:
        logging.error(f"Respuesta de la API no es JSON válido: {e}. Contenido: {r.text[:500]}")
        raise RuntimeError(f"Error al parsear respuesta JSON de la API: {e}")


def cookies_validas(session, timeout):
    try:
        r = session.post(
            API_URL, data={"id_empresa": 9, "id_agenda": 7}, timeout=timeout
        )
        if r.status_code != 200:
            return False
        # Verificar si la respuesta es JSON válido
        try:
            r.json()
            return True
        except json.JSONDecodeError:
            return False
    except Exception:
        return False
