import json
from pathlib import Path

STATE_FILE = Path("state.json")


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


def guardar_estado(fecha):
    STATE_FILE.write_text(
        json.dumps({"ultima_fecha_notificada": fecha}, indent=2)
    )


def obtener_tramite_ultima_fecha(data):
    if not data.get("disponibilidades"):
        return None

    tramites = []
    for bloque in data["disponibilidades"]:
        tramites.extend(bloque.keys())

    if not tramites:
        return None

    tramites.sort(key=lambda x: x["fecha"])
    f = tramites[0].fecha
    # Validación básica: asumir formato YYYYMMDD (8 dígitos)
    if len(f) != 8 or not f.isdigit():
        return None
    return f"{f[6:8]}/{f[4:6]}/{f[0:4]}"


def guardar_nombre_tramite(nombre):
    state = cargar_estado()
    state["nombre_tramite"] = nombre
    STATE_FILE.write_text(json.dumps(state, indent=2))
