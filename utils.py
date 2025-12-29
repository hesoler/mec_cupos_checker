import json
from pathlib import Path

STATE_FILE = "state.json"


def cargar_estado():
    if not Path(STATE_FILE).exists():
        return {"ultima_fecha_notificada": None}

    try:
        state = json.loads(Path(STATE_FILE).read_text())
        if not state or not isinstance(state, dict):
            return {"ultima_fecha_notificada": None}
        return state
    except json.JSONDecodeError:
        return {"ultima_fecha_notificada": None}


def guardar_estado(fecha):
    Path(STATE_FILE).write_text(
        json.dumps({"ultima_fecha_notificada": fecha}, indent=2)
    )


def obtener_primera_fecha(data):
    if not data.get("disponibilidades"):
        return None

    fechas = []
    for bloque in data["disponibilidades"]:
        fechas.extend(bloque.keys())

    if not fechas:
        return None

    fechas.sort()
    f = fechas[0]
    # Validación básica: asumir formato YYYYMMDD (8 dígitos)
    if len(f) != 8 or not f.isdigit():
        return None
    return f"{f[6:8]}/{f[4:6]}/{f[0:4]}"
