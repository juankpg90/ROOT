"""Lista de vigilancia de precios con umbrales de compra.

Los precios se registran a mano (lo que se ve en el checkout) o con un intento de
lectura de la página de Amazon, que se marca como fuente 'web-no-verificado':
Amazon cambia su HTML y puede bloquear la consulta, y el precio de la página no
incluye envío ni cargos de importación. Ninguna alerta reemplaza revisar el checkout.
"""
import csv
import re
import urllib.request
from datetime import date
from pathlib import Path

from arbitraje.config import DATA_DIR

CAMPOS = ["id", "producto", "url", "umbral_usd", "descartar_usd", "ultimo_precio_usd",
          "fecha_precio", "fuente", "notas"]


def _ruta(data_dir, nombre):
    return Path(data_dir) / nombre


def leer(data_dir=DATA_DIR):
    with open(_ruta(data_dir, "vigilancia.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar(items, data_dir=DATA_DIR):
    with open(_ruta(data_dir, "vigilancia.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        for i in items:
            w.writerow({k: i.get(k, "") for k in CAMPOS})


def estado(item):
    """'COMPRAR', 'DESCARTAR', 'VIGILAR' o 'SIN PRECIO'."""
    if not item.get("ultimo_precio_usd"):
        return "SIN PRECIO"
    precio = float(item["ultimo_precio_usd"])
    if precio <= float(item["umbral_usd"]):
        return "COMPRAR"
    if item.get("descartar_usd") and precio > float(item["descartar_usd"]):
        return "DESCARTAR"
    return "VIGILAR"


def registrar_precio(items, id_, precio_usd, fuente="manual", hoy=None, data_dir=DATA_DIR):
    hoy = (hoy or date.today()).isoformat()
    for item in items:
        if item["id"] == id_:
            item.update(ultimo_precio_usd=f"{precio_usd:.2f}", fecha_precio=hoy, fuente=fuente)
            with open(_ruta(data_dir, "historial_precios.csv"), "a", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\n").writerow([hoy, id_, f"{precio_usd:.2f}", fuente])
            return item
    raise ValueError(f"No existe '{id_}' en la lista de vigilancia")


_PATRONES_PRECIO = [
    r'"priceAmount"\s*:\s*([0-9]+(?:\.[0-9]{1,2})?)',
    r'<span class="a-offscreen">\s*\$([0-9][0-9,]*\.[0-9]{2})\s*</span>',
]


def extraer_precio(html):
    for patron in _PATRONES_PRECIO:
        m = re.search(patron, html)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def consultar_precio(url, timeout=20):
    """Intenta leer el precio de una página de producto. Devuelve None si no lo logra."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    return extraer_precio(html)
