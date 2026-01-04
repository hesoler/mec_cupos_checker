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
