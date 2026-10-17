"""Tracker de ciclos: compras, ventas, utilidad, ROI, rotación y capital disponible."""
import csv
from datetime import date
from pathlib import Path

from arbitraje.config import DATA_DIR

CAMPOS = [
    "id", "producto", "url", "fecha_compra", "precio_usd", "costo_cop", "fecha_llegada",
    "canales_publicacion", "fecha_venta", "precio_venta_cop", "canal_venta", "comision_cop",
    "envio_cop", "empaque_cop", "publicidad_cop", "otros_cop", "reserva_cop",
    "garantia_vence", "notas",
]
GASTOS_VENTA = ["comision_cop", "envio_cop", "empaque_cop", "publicidad_cop", "otros_cop"]


def ruta(data_dir=DATA_DIR):
    return Path(data_dir) / "ciclos.csv"


def leer(data_dir=DATA_DIR):
    with open(ruta(data_dir), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar(ciclos, data_dir=DATA_DIR):
    with open(ruta(data_dir), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator="\n")
        w.writeheader()
        for c in ciclos:
            w.writerow({k: c.get(k, "") for k in CAMPOS})


def _num(v):
    return float(v) if v not in (None, "") else 0.0


def _fecha(v):
    return date.fromisoformat(v) if v else None


def buscar(ciclos, id_):
    for c in ciclos:
        if c["id"] == str(id_):
            return c
    raise ValueError(f"No existe el ciclo {id_}")


def vendido(c):
    return bool(c.get("fecha_venta"))


def metricas(c):
    """Utilidad, margen, ROI y rotación de un ciclo vendido (None si no se ha vendido)."""
    if not vendido(c):
        return None
    costo = _num(c["costo_cop"])
    venta = _num(c["precio_venta_cop"])
    utilidad = venta - costo - sum(_num(c.get(k)) for k in GASTOS_VENTA)
    llegada, venta_f = _fecha(c.get("fecha_llegada")), _fecha(c["fecha_venta"])
    return {
        "utilidad": utilidad,
        "margen": utilidad / venta * 100 if venta else 0.0,
        "roi": utilidad / costo * 100 if costo else 0.0,
        "dias_rotacion": (venta_f - llegada).days if llegada else None,
    }


def capital(ciclos, capital_inicial, hoy=None):
    """Capital disponible = inicial + utilidades realizadas − costo de inventario sin vender
    − reservas de garantía vigentes."""
    hoy = hoy or date.today()
    utilidades = sum(metricas(c)["utilidad"] for c in ciclos if vendido(c))
    inventario = sum(_num(c["costo_cop"]) for c in ciclos if not vendido(c))
    reservas = sum(
        _num(c.get("reserva_cop")) for c in ciclos
        if vendido(c) and (_fecha(c.get("garantia_vence")) or hoy) >= hoy
    )
    total = capital_inicial + utilidades
    return {
        "capital_total": total,
        "utilidades_realizadas": utilidades,
        "en_inventario": inventario,
        "reservas_vigentes": reservas,
        "disponible": total - inventario - reservas,
    }


def nuevo(ciclos, **campos):
    siguiente = max((int(c["id"]) for c in ciclos), default=0) + 1
    ciclo = {k: "" for k in CAMPOS}
    ciclo.update({k: v for k, v in campos.items() if v is not None})
    ciclo["id"] = str(siguiente)
    ciclos.append(ciclo)
    return ciclo


def actualizar(ciclos, id_, **campos):
    c = buscar(ciclos, id_)
    desconocidos = set(campos) - set(CAMPOS)
    if desconocidos:
        raise ValueError(f"Campos desconocidos: {', '.join(sorted(desconocidos))}")
    c.update({k: str(v) for k, v in campos.items() if v is not None})
    return c
