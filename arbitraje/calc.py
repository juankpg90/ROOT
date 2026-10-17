"""Calculadora de márgenes: utilidad, margen, ROI y precio mínimo de venta."""
from dataclasses import dataclass


@dataclass
class Resultado:
    escenario: str
    venta: float
    comision: float
    utilidad: float
    margen: float  # % sobre precio de venta
    roi: float  # % sobre capital invertido


def costo_total(precio_usd, tasa, envio_usd=0.0, importacion_usd=0.0, otros_cop=0.0):
    """Costo total unitario en COP puesto en Bogotá."""
    return (precio_usd + envio_usd + importacion_usd) * tasa + otros_cop


def evaluar(costo, venta, comision_pct=0.0, gastos_venta=0.0, escenario=""):
    """gastos_venta: envío asumido + empaque + publicidad + otros, en COP."""
    comision = venta * comision_pct
    utilidad = venta - costo - comision - gastos_venta
    margen = utilidad / venta * 100 if venta else 0.0
    roi = utilidad / costo * 100 if costo else 0.0
    return Resultado(escenario, venta, comision, utilidad, margen, roi)


def precio_minimo(costo, comision_pct=0.0, gastos_venta=0.0, roi_objetivo=0.0):
    """Precio de venta que deja exactamente `roi_objetivo` (fracción) sobre el costo."""
    if comision_pct >= 1:
        raise ValueError("La comisión debe ser menor al 100%")
    return (costo * (1 + roi_objetivo) + gastos_venta) / (1 - comision_pct)


def precio_max_compra_usd(venta, tasa, comision_pct=0.0, gastos_venta=0.0, roi_objetivo=0.0,
                          envio_usd=0.0, importacion_usd=0.0, otros_cop=0.0):
    """Precio máximo en Amazon (USD) para lograr `roi_objetivo` vendiendo a `venta`."""
    costo_max = (venta * (1 - comision_pct) - gastos_venta) / (1 + roi_objetivo)
    return (costo_max - otros_cop) / tasa - envio_usd - importacion_usd
