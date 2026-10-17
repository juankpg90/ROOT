import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from arbitraje import calc, tracker, vigilancia
from arbitraje.cli import main

DATA = Path(__file__).resolve().parent.parent / "data"


class TestCalc(unittest.TestCase):
    def test_airtag_base(self):
        costo = calc.costo_total(64.99, 3250)
        r = calc.evaluar(costo, 420000)
        self.assertAlmostEqual(r.utilidad, 208782.5)
        self.assertAlmostEqual(r.roi, 98.85, places=1)

    def test_comision_y_gastos(self):
        r = calc.evaluar(100000, 200000, comision_pct=0.19, gastos_venta=10000)
        self.assertAlmostEqual(r.utilidad, 200000 - 100000 - 38000 - 10000)

    def test_precio_minimo_da_roi_objetivo(self):
        p = calc.precio_minimo(200000, 0.19, 15000, 0.30)
        self.assertAlmostEqual(calc.evaluar(200000, p, 0.19, 15000).roi, 30.0)

    def test_max_compra_inverso(self):
        usd = calc.precio_max_compra_usd(420000, 3250, 0.19, 15000, 0.30)
        costo = calc.costo_total(usd, 3250)
        self.assertAlmostEqual(calc.precio_minimo(costo, 0.19, 15000, 0.30), 420000)


class TestTracker(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for f in DATA.iterdir():
            shutil.copy(f, self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_ciclo_1(self):
        m = tracker.metricas(tracker.buscar(tracker.leer(self.dir), 1))
        self.assertEqual(m["utilidad"], 127500)
        self.assertAlmostEqual(m["margen"], 41.13, places=1)
        self.assertAlmostEqual(m["roi"], 69.86, places=1)
        self.assertEqual(m["dias_rotacion"], 42)

    def test_capital(self):
        ciclos = tracker.leer(self.dir)
        self.assertEqual(tracker.capital(ciclos, 182500, date(2026, 10, 17))["disponible"], 280000)
        # La reserva se libera al vencer la garantía.
        self.assertEqual(tracker.capital(ciclos, 182500, date(2026, 11, 2))["disponible"], 310000)

    def test_flujo_completo(self):
        d = str(self.dir)
        self.assertEqual(main(["--data", d, "comprar", "AirTag x4", "64.99", "211500"]), 0)
        k = tracker.capital(tracker.leer(self.dir), 182500, date(2026, 10, 17))
        self.assertEqual(k["disponible"], 280000 - 211500)
        main(["--data", d, "llegada", "2", "--fecha", "2026-11-01"])
        main(["--data", d, "vender", "2", "420000", "--fecha", "2026-11-20"])
        m = tracker.metricas(tracker.buscar(tracker.leer(self.dir), 2))
        self.assertEqual(m["utilidad"], 208500)
        self.assertEqual(m["dias_rotacion"], 19)

    def test_vender_mercadolibre_aplica_comision(self):
        d = str(self.dir)
        main(["--data", d, "comprar", "X", "50", "160000"])
        main(["--data", d, "vender", "2", "300000", "--canal", "mercadolibre", "--envio-cop", "10000"])
        m = tracker.metricas(tracker.buscar(tracker.leer(self.dir), 2))
        self.assertEqual(m["utilidad"], 300000 - 160000 - 57000 - 10000)


class TestVigilancia(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for f in DATA.iterdir():
            shutil.copy(f, self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_estados(self):
        items = vigilancia.leer(self.dir)
        historial = self.dir / "historial_precios.csv"
        antes = len(historial.read_text().splitlines())
        ugreen = vigilancia.registrar_precio(items, "ugreen160", 61.5, data_dir=self.dir)
        self.assertEqual(vigilancia.estado(ugreen), "COMPRAR")
        vigilancia.registrar_precio(items, "ugreen160", 65, data_dir=self.dir)
        self.assertEqual(vigilancia.estado(ugreen), "VIGILAR")
        vigilancia.registrar_precio(items, "ugreen160", 71, data_dir=self.dir)
        self.assertEqual(vigilancia.estado(ugreen), "DESCARTAR")
        self.assertEqual(len(historial.read_text().splitlines()), antes + 3)

    def test_extraer_precio(self):
        self.assertEqual(vigilancia.extraer_precio('<span class="a-offscreen">$1,064.99</span>'), 1064.99)
        self.assertEqual(vigilancia.extraer_precio('{"priceAmount":64.99}'), 64.99)
        self.assertIsNone(vigilancia.extraer_precio("<html></html>"))

    def test_codigo_salida_con_alerta(self):
        d = str(self.dir)
        main(["--data", d, "precio", "airtag4", "64.99"])
        self.assertEqual(main(["--data", d, "vigilar", "--codigo-salida"]), 1)


if __name__ == "__main__":
    unittest.main()
