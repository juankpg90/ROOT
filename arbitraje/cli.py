"""CLI: python -m arbitraje <comando> ...  (ver README.md)"""
import argparse
from datetime import date

from arbitraje import calc, tracker, vigilancia
from arbitraje.config import DATA_DIR, cargar, comision_canal


def cop(v):
    return f"${v:,.0f}".replace(",", ".")


def _escenarios(texto):
    """'conservador=380000,base=420000' -> [('conservador', 380000.0), ...]"""
    pares = []
    for parte in texto.split(","):
        nombre, _, valor = parte.partition("=")
        if not valor:
            raise argparse.ArgumentTypeError(f"Escenario mal formado: '{parte}' (use nombre=precio)")
        pares.append((nombre.strip(), float(valor)))
    return pares


def cmd_calc(args, cfg):
    tasa = args.tasa or cfg["tasa_efectiva_cop_usd"]
    comision = args.comision if args.comision is not None else comision_canal(cfg, args.canal)
    roi_min = args.roi_min if args.roi_min is not None else cfg["roi_minimo"]
    total_usd = args.usd + args.envio_usd + args.importacion_usd
    costo = calc.costo_total(args.usd, tasa, args.envio_usd, args.importacion_usd, args.otros_cop)

    print(f"Costo total: {cop(costo)}  (USD {total_usd:.2f} × {cop(tasa)[1:]} + {cop(args.otros_cop)} otros)")
    print(f"Canal: {args.canal}  comisión {comision * 100:.1f}%  gastos de venta {cop(args.gastos_venta)}")
    if total_usd > cfg["max_compra_usd"]:
        print(f"⚠ Excede el máximo por compra (USD {cfg['max_compra_usd']}).")
    print()
    print(f"{'Escenario':<14}{'Venta':>12}{'Comisión':>11}{'Utilidad':>12}{'Margen':>9}{'ROI':>8}")
    for nombre, venta in args.escenarios:
        r = calc.evaluar(costo, venta, comision, args.gastos_venta, nombre)
        print(f"{r.escenario:<14}{cop(r.venta):>12}{cop(r.comision):>11}{cop(r.utilidad):>12}"
              f"{r.margen:>8.1f}%{r.roi:>7.1f}%")
    print()
    print(f"Punto de equilibrio: {cop(calc.precio_minimo(costo, comision, args.gastos_venta))}")
    print(f"Precio mínimo aceptable (ROI {roi_min * 100:.0f}%): "
          f"{cop(calc.precio_minimo(costo, comision, args.gastos_venta, roi_min))}")
    if args.capital is not None and costo > args.capital:
        print(f"⚠ El costo supera el capital disponible ({cop(args.capital)}).")
    return 0


def cmd_maxcompra(args, cfg):
    tasa = args.tasa or cfg["tasa_efectiva_cop_usd"]
    comision = args.comision if args.comision is not None else comision_canal(cfg, args.canal)
    roi_min = args.roi_min if args.roi_min is not None else cfg["roi_minimo"]
    usd = calc.precio_max_compra_usd(args.venta, tasa, comision, args.gastos_venta, roi_min)
    print(f"Vendiendo en {cop(args.venta)} por {args.canal} con ROI ≥ {roi_min * 100:.0f}%: "
          f"pagar como máximo USD {usd:.2f} (a {cop(tasa)[1:]} COP/USD, envío e importación USD 0)")
    return 0


def _imprimir_ciclo(c):
    m = tracker.metricas(c)
    estado = "VENDIDO" if m else ("EN INVENTARIO" if c["fecha_llegada"] else "EN TRÁNSITO")
    print(f"#{c['id']} {c['producto']} [{estado}]")
    print(f"   compra: USD {c['precio_usd'] or '?'} → {cop(float(c['costo_cop'] or 0))}"
          f"  llegada: {c['fecha_llegada'] or '-'}  publicado: {c['canales_publicacion'] or '-'}")
    if m:
        dias = f"{m['dias_rotacion']} días" if m["dias_rotacion"] is not None else "?"
        print(f"   venta: {cop(float(c['precio_venta_cop']))} por {c['canal_venta']} el {c['fecha_venta']}"
              f"  utilidad {cop(m['utilidad'])}  margen {m['margen']:.1f}%  ROI {m['roi']:.1f}%"
              f"  rotación {dias}")
    elif c["fecha_llegada"]:
        dias = (date.today() - date.fromisoformat(c["fecha_llegada"])).days
        print(f"   {dias} días en inventario")


def cmd_ciclos(args, cfg):
    for c in tracker.leer(args.data):
        _imprimir_ciclo(c)
    return 0


def cmd_capital(args, cfg):
    k = tracker.capital(tracker.leer(args.data), cfg["capital_inicial_cop"])
    print(f"Capital inicial:          {cop(cfg['capital_inicial_cop'])}")
    print(f"Utilidades realizadas:  + {cop(k['utilidades_realizadas'])}")
    print(f"Capital total:            {cop(k['capital_total'])}")
    print(f"En inventario/tránsito: − {cop(k['en_inventario'])}")
    print(f"Reservas de garantía:   − {cop(k['reservas_vigentes'])}")
    tasa = cfg["tasa_efectiva_cop_usd"]
    print(f"Disponible:               {cop(k['disponible'])}  (≈ USD {k['disponible'] / tasa:.0f} a {cop(tasa)[1:]})")
    return 0


def cmd_comprar(args, cfg):
    ciclos = tracker.leer(args.data)
    c = tracker.nuevo(ciclos, producto=args.producto, url=args.url, precio_usd=str(args.usd),
                      costo_cop=f"{args.costo_cop:.0f}", fecha_compra=args.fecha or date.today().isoformat(),
                      notas=args.notas)
    tracker.guardar(ciclos, args.data)
    print(f"Registrado ciclo #{c['id']}: {c['producto']} — {cop(args.costo_cop)} "
          f"(tasa efectiva {cop(args.costo_cop / args.usd)[1:]} COP/USD)")
    return 0


def cmd_actualizar(args, cfg):
    ciclos = tracker.leer(args.data)
    campos = dict(kv.split("=", 1) for kv in args.campos)
    c = tracker.actualizar(ciclos, args.id, **campos)
    tracker.guardar(ciclos, args.data)
    _imprimir_ciclo(c)
    return 0


def cmd_llegada(args, cfg):
    ciclos = tracker.leer(args.data)
    c = tracker.actualizar(ciclos, args.id, fecha_llegada=args.fecha or date.today().isoformat())
    tracker.guardar(ciclos, args.data)
    _imprimir_ciclo(c)
    return 0


def cmd_vender(args, cfg):
    ciclos = tracker.leer(args.data)
    comision = args.comision_cop
    if comision is None:
        comision = args.precio * comision_canal(cfg, args.canal)
    c = tracker.actualizar(
        ciclos, args.id, fecha_venta=args.fecha or date.today().isoformat(),
        precio_venta_cop=f"{args.precio:.0f}", canal_venta=args.canal, comision_cop=f"{comision:.0f}",
        envio_cop=f"{args.envio_cop:.0f}", empaque_cop=f"{args.empaque_cop:.0f}",
        publicidad_cop=f"{args.publicidad_cop:.0f}", otros_cop=f"{args.otros_cop:.0f}",
        reserva_cop=f"{args.reserva_cop:.0f}", garantia_vence=args.garantia_vence,
    )
    tracker.guardar(ciclos, args.data)
    _imprimir_ciclo(c)
    return 0


def cmd_vigilar(args, cfg):
    items = vigilancia.leer(args.data)
    if args.consultar:
        for item in items:
            if item["url"]:
                precio = vigilancia.consultar_precio(item["url"])
                if precio is None:
                    print(f"· {item['id']}: no se pudo leer el precio de la página")
                else:
                    vigilancia.registrar_precio(items, item["id"], precio, "web-no-verificado", data_dir=args.data)
        vigilancia.guardar(items, args.data)
    alertas = 0
    for item in items:
        est = vigilancia.estado(item)
        precio = f"USD {item['ultimo_precio_usd']} ({item['fecha_precio']}, {item['fuente']})" \
            if item["ultimo_precio_usd"] else "sin precio registrado"
        print(f"[{est:^10}] {item['id']:<10} {item['producto']} — umbral ≤ USD {item['umbral_usd']} — {precio}")
        if est == "COMPRAR":
            alertas += 1
            print(f"             → Verificar checkout: envío e importación USD 0. {item['notas']}")
    return 1 if args.codigo_salida and alertas else 0


def cmd_precio(args, cfg):
    items = vigilancia.leer(args.data)
    item = vigilancia.registrar_precio(items, args.id, args.usd, args.fuente, data_dir=args.data)
    vigilancia.guardar(items, args.data)
    print(f"{item['producto']}: USD {item['ultimo_precio_usd']} → {vigilancia.estado(item)}")
    return 0


def construir_parser():
    p = argparse.ArgumentParser(prog="arbitraje", description="Arbitraje Amazon USA → Colombia")
    p.add_argument("--data", default=DATA_DIR, help="Carpeta de datos (por defecto ./data)")
    sub = p.add_subparsers(dest="comando", required=True)

    def canal_args(sp):
        sp.add_argument("--tasa", type=float, help="COP por USD efectivos (por defecto config.json)")
        sp.add_argument("--canal", default="marketplace")
        sp.add_argument("--comision", type=float, help="Comisión como fracción (anula la del canal)")
        sp.add_argument("--gastos-venta", type=float, default=0.0,
                        help="Envío asumido + empaque + publicidad + otros (COP)")
        sp.add_argument("--roi-min", type=float, help="ROI mínimo aceptable como fracción")

    s = sub.add_parser("calc", help="Utilidad, margen y ROI por escenario")
    s.add_argument("usd", type=float, help="Precio en Amazon (USD)")
    s.add_argument("escenarios", type=_escenarios,
                   help="Precios de venta: conservador=380000,base=420000,optimista=450000,rapida=360000")
    s.add_argument("--envio-usd", type=float, default=0.0)
    s.add_argument("--importacion-usd", type=float, default=0.0)
    s.add_argument("--otros-cop", type=float, default=0.0, help="Transporte local, cambio, etc.")
    s.add_argument("--capital", type=float, help="Capital disponible para validar la compra")
    canal_args(s)
    s.set_defaults(func=cmd_calc)

    s = sub.add_parser("maxcompra", help="Precio máximo a pagar en Amazon para un precio de venta")
    s.add_argument("venta", type=float, help="Precio de venta esperado (COP)")
    canal_args(s)
    s.set_defaults(func=cmd_maxcompra)

    sub.add_parser("ciclos", help="Lista los ciclos").set_defaults(func=cmd_ciclos)
    sub.add_parser("capital", help="Capital disponible y reservas").set_defaults(func=cmd_capital)

    s = sub.add_parser("comprar", help="Registra una compra (abre un ciclo)")
    s.add_argument("producto")
    s.add_argument("usd", type=float, help="Precio pagado en Amazon (USD)")
    s.add_argument("costo_cop", type=float, help="Cargo real en la tarjeta (COP)")
    s.add_argument("--url", default="")
    s.add_argument("--fecha")
    s.add_argument("--notas", default="")
    s.set_defaults(func=cmd_comprar)

    s = sub.add_parser("llegada", help="Registra la llegada del producto")
    s.add_argument("id")
    s.add_argument("--fecha")
    s.set_defaults(func=cmd_llegada)

    s = sub.add_parser("vender", help="Registra la venta y cierra el ciclo")
    s.add_argument("id")
    s.add_argument("precio", type=float, help="Dinero recibido por la venta (COP)")
    s.add_argument("--canal", default="marketplace")
    s.add_argument("--fecha")
    s.add_argument("--comision-cop", type=float, help="Comisión real cobrada (por defecto la del canal)")
    for campo in ("envio", "empaque", "publicidad", "otros", "reserva"):
        s.add_argument(f"--{campo}-cop", type=float, default=0.0)
    s.add_argument("--garantia-vence", default="")
    s.set_defaults(func=cmd_vender)

    s = sub.add_parser("actualizar", help="Edita campos de un ciclo: campo=valor ...")
    s.add_argument("id")
    s.add_argument("campos", nargs="+")
    s.set_defaults(func=cmd_actualizar)

    s = sub.add_parser("vigilar", help="Muestra la lista de vigilancia y alertas")
    s.add_argument("--consultar", action="store_true",
                   help="Intenta leer precios de las páginas (no verificado; puede fallar)")
    s.add_argument("--codigo-salida", action="store_true", help="Sale con 1 si hay alguna alerta")
    s.set_defaults(func=cmd_vigilar)

    s = sub.add_parser("precio", help="Registra un precio observado para un producto vigilado")
    s.add_argument("id")
    s.add_argument("usd", type=float)
    s.add_argument("--fuente", default="manual")
    s.set_defaults(func=cmd_precio)
    return p


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args, cargar(args.data))
    except ValueError as e:
        print(f"Error: {e}")
        return 2
