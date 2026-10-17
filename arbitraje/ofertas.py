"""Busca productos con descuento en los resultados de búsqueda de Amazon.

Los precios son los que ve un visitante de EE. UU.: no confirman el envío a
Colombia ni el vendedor. Sirven para encontrar candidatos, no para comprar.
"""
import html
import re
import time
import urllib.parse

from arbitraje.vigilancia import descargar

_INICIO_RESULTADO = r'(?=<div[^>]+data-asin="[A-Z0-9]{10}"[^>]+data-component-type="s-search-result")'


def _num(texto):
    return float(texto.replace(",", ""))


def parsear_resultados(pagina):
    """Lista de dicts (asin, titulo, precio, lista, descuento, estrellas, resenas, patrocinado)."""
    productos = []
    for bloque in re.split(_INICIO_RESULTADO, pagina)[1:]:
        asin = re.search(r'data-asin="([A-Z0-9]{10})"', bloque).group(1)
        precio = re.search(r'<span class="a-price"[^>]*><span class="a-offscreen">\$([\d,]+\.\d\d)', bloque)
        if not precio:
            continue
        lista = re.search(r'a-text-price"[^>]*><span class="a-offscreen">\$([\d,]+\.\d\d)', bloque)
        # La marca y el nombre pueden venir en <h2> separados.
        titulo = " ".join(re.sub(r"<[^>]+>", " ", t) for t in re.findall(r"<h2[^>]*>(.*?)</h2>", bloque, re.S))
        estrellas = re.search(r'([\d.]+) out of 5 stars', bloque)
        resenas = re.search(r'aria-label="([\d,]+) ratings?"', bloque)
        p = _num(precio.group(1))
        l = _num(lista.group(1)) if lista else None
        productos.append({
            "asin": asin,
            "titulo": re.sub(r"\s+", " ", html.unescape(titulo)).strip(),
            "precio": p,
            "lista": l,
            "descuento": round((1 - p / l) * 100) if l and l > p else 0,
            "estrellas": float(estrellas.group(1)) if estrellas else None,
            "resenas": int(resenas.group(1).replace(",", "")) if resenas else 0,
            "patrocinado": "Sponsored" in bloque[:3000],
        })
    return productos


def buscar(consultas, pausa=3):
    """Ejecuta cada búsqueda y devuelve los productos sin repetir ASIN."""
    vistos, productos = set(), []
    for i, consulta in enumerate(consultas):
        if i:
            time.sleep(pausa)
        pagina = descargar("https://www.amazon.com/s?" + urllib.parse.urlencode({"k": consulta}))
        for p in parsear_resultados(pagina or ""):
            if p["asin"] not in vistos:
                vistos.add(p["asin"])
                productos.append(dict(p, consulta=consulta))
    return productos


def filtrar(productos, max_usd, min_usd=20, min_descuento=20, min_resenas=500):
    """Candidatos: dentro del capital, con descuento real y muchas reseñas; sin reacondicionados."""
    return sorted(
        (p for p in productos
         if min_usd <= p["precio"] <= max_usd
         and p["descuento"] >= min_descuento
         and p["resenas"] >= min_resenas
         and "renewed" not in p["titulo"].lower()),
        key=lambda p: -p["descuento"])
