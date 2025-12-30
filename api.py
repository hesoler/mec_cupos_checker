import json
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
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'es-419,es;q=0.9,es-ES;q=0.8,en;q=0.7,en-GB;q=0.6,en-US;q=0.5',
        'Referer': 'https://bpmgob.mec.gub.uy/',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
    })

    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    return session


def consultar_disponibilidades(session, token, id_recurso, id_agenda, timeout):
    payload = {
        "method": "POST",
        "url": "https://sae.mec.gub.uy/sae-admin/rest/consultas/disponibilidades_por_recurso",
        "token": token,
        "id_empresa": 9,
        "id_agenda": id_agenda,
        "id_recurso": id_recurso,
        "idioma": "es",
    }

    r = session.post(API_URL, data=payload, timeout=timeout)

    if "text/html" in r.headers.get("Content-Type", ""):
        raise RuntimeError("Respuesta HTML recibida (token inválido o sesión caída)")

    r.raise_for_status()
    return r.json()


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


def obtener_nombre_tramite(session, token, id_agenda, id_recurso, timeout):
    payload = {
        "method": "POST",
        "url": "https://sae.mec.gub.uy/sae-admin/rest/consultas/recursos_por_agenda",
        "token": token,
        "id_empresa": 9,
        "id_agenda": id_agenda,
        "id_recurso": id_recurso,
        "idioma": "es",
    }

    r = session.post(
        "https://bpmgob.mec.gub.uy/etapas/agenda_sae_api_recursos",
        data=payload,
        timeout=timeout
    )
    r.raise_for_status()
    data = r.json()
    recursos = r.json().get("recursos", [])
    for recurso in recursos:
        if recurso.get("id_recurso") == id_recurso:
            return recurso.get("nombre")

    return None
