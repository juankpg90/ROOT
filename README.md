# Arbitraje Amazon USA → Colombia

Herramientas de línea de comandos (Python 3.10+, sin dependencias) para operar el
modelo de capital rotativo: comprar 1 unidad en Amazon USA, vender en Colombia,
recuperar capital y reinvertir.

```
python -m arbitraje <comando> --help
```

## Datos (`data/`)

| Archivo | Contenido |
|---|---|
| `config.json` | Tasa efectiva COP/USD, capital inicial, ROI mínimo, máximo por compra y comisión de cada canal |
| `ciclos.csv` | Un registro por ciclo (compra → llegada → venta). Incluye el ciclo 1 cerrado |
| `vigilancia.csv` | Productos vigilados con su umbral de compra (y de descarte) |
| `historial_precios.csv` | Cada precio registrado, con fecha y fuente |

Son CSV planos: se pueden abrir en Excel/Sheets y versionar con git.

## 1. Calculadora de márgenes

```
# AirTag x4 a USD 64,99, venta en Marketplace (0%), tasa de config.json
python -m arbitraje calc 64.99 rapida=380000,base=420000,optimista=450000 --capital 280000

# Misma compra vendida en Mercado Libre (19%) asumiendo $15.000 de envío
python -m arbitraje calc 64.99 base=420000 --canal mercadolibre --gastos-venta 15000

# ¿Cuánto puedo pagar en Amazon como máximo si vendo en $420.000?
python -m arbitraje maxcompra 420000 --roi-min 0.5
```

Muestra costo total, utilidad, margen y ROI por escenario, el punto de equilibrio y
el precio mínimo aceptable (el que deja el ROI mínimo de `config.json`, 30% por
defecto). Opciones: `--tasa`, `--envio-usd`, `--importacion-usd`, `--otros-cop`,
`--comision`, `--roi-min`.

## 2. Tracker de ciclos

```
python -m arbitraje comprar "Apple AirTag x4" 64.99 211500 --url https://www.amazon.com/dp/B0D54JZTHY
python -m arbitraje llegada 2 --fecha 2026-11-01
python -m arbitraje actualizar 2 canales_publicacion="marketplace;mercadolibre"
python -m arbitraje vender 2 420000 --canal marketplace --reserva-cop 40000 --garantia-vence 2026-12-05
python -m arbitraje ciclos
python -m arbitraje capital
```

- `costo_cop` en `comprar` es **el cargo real de la tarjeta** (la tasa efectiva se calcula sola).
- `vender` toma la comisión del canal salvo que se pase `--comision-cop` con la real.
  También acepta `--envio-cop`, `--empaque-cop`, `--publicidad-cop`, `--otros-cop`.
- Rotación = días entre llegada y venta.
- **Capital disponible** = capital inicial + utilidades realizadas − costo de lo que
  está en tránsito/inventario − reservas de garantía vigentes. La reserva se libera
  sola cuando pasa `garantia_vence`. Las ventas sin registrar no cuentan: no se
  reinvierte dinero no recibido.

## 3. Vigilante de precios

```
python -m arbitraje precio airtag4 64.99           # precio visto en el checkout
python -m arbitraje vigilar                        # estado de la lista
python -m arbitraje vigilar --consultar            # intenta leer los precios de Amazon
python -m arbitraje vigilar --codigo-salida        # sale con 1 si hay alerta (para cron)
```

Estados: `COMPRAR` (precio ≤ umbral), `VIGILAR`, `DESCARTAR` (precio > límite de
descarte) y `SIN PRECIO`. Umbrales iniciales: AirTag x4 ≤ USD 70, UGREEN 160W ≤ USD 62
(descartar > 70), MX Master 3S ≤ USD 80. Se agregan o cambian editando `vigilancia.csv`.

`--consultar` es un intento de leer la página de Amazon: puede fallar (Amazon bloquea
o cambia su HTML) y el precio de la página **no incluye envío ni importación**. Por
eso esos precios se guardan con fuente `web-no-verificado`. La decisión de compra
siempre se confirma en el checkout.

Ejemplo de alerta diaria con cron (en tu equipo):

```
0 9 * * * cd ~/ROOT && python3 -m arbitraje vigilar --consultar --codigo-salida || notify-send "Arbitraje" "Hay un producto bajo el umbral"
```

## Tests

```
python -m unittest -v
```
