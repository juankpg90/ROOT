import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def cargar(data_dir=DATA_DIR):
    with open(Path(data_dir) / "config.json", encoding="utf-8") as f:
        return json.load(f)


def comision_canal(cfg, canal):
    try:
        return cfg["canales"][canal]["comision"]
    except KeyError:
        disponibles = ", ".join(cfg["canales"])
        raise ValueError(f"Canal desconocido '{canal}'. Disponibles: {disponibles}") from None
