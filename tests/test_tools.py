"""Pruebas de las herramientas (no requieren modelo ni API key).

Ejecutar con:  python -m unittest discover tests
"""

import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_TMP = tempfile.TemporaryDirectory()
os.environ["GASTOS_DATA_FILE"] = str(Path(_TMP.name) / "gastos.json")

# Se importa tools.py directamente para no requerir google-adk en los tests.
_spec = importlib.util.spec_from_file_location(
    "tools", Path(__file__).resolve().parents[1] / "gestor_gastos" / "tools.py"
)
tools = importlib.util.module_from_spec(_spec)
sys.modules["tools"] = tools
_spec.loader.exec_module(tools)


class TestHerramientas(unittest.TestCase):
    def setUp(self):
        tools._DATA_FILE.unlink(missing_ok=True)

    # --- registrar_gasto ---
    def test_registrar_ok(self):
        r = tools.registrar_gasto("Pan", 1500, "Alimentación", "2026-11-01")
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["gasto"]["categoria"], "alimentacion")
        self.assertEqual(r["gasto"]["id"], 1)

    def test_registrar_fecha_por_defecto_hoy(self):
        r = tools.registrar_gasto("Café", 800, "ocio")
        self.assertEqual(r["gasto"]["fecha"], date.today().isoformat())

    def test_registrar_invalidos(self):
        self.assertEqual(tools.registrar_gasto("", 10, "ocio")["status"], "error")
        self.assertEqual(tools.registrar_gasto("x", -5, "ocio")["status"], "error")
        self.assertEqual(tools.registrar_gasto("x", "abc", "ocio")["status"], "error")
        self.assertEqual(tools.registrar_gasto("x", 10, "mascotas")["status"], "error")
        self.assertEqual(tools.registrar_gasto("x", 10, "ocio", "01/11/2026")["status"], "error")
        self.assertEqual(tools.registrar_gasto("x", 10, "ocio", "2999-01-01")["status"], "error")

    # --- buscar_gastos ---
    def test_buscar_vacio(self):
        self.assertEqual(tools.buscar_gastos()["status"], "empty")

    def test_buscar_filtros(self):
        tools.registrar_gasto("Nafta", 30000, "transporte", "2026-11-05")
        tools.registrar_gasto("Super", 45000, "alimentacion", "2026-11-02")
        tools.registrar_gasto("Colectivo", 1000, "transporte", "2026-10-20")
        r = tools.buscar_gastos(categoria="transporte", desde="2026-11-01")
        self.assertEqual(r["cantidad"], 1)
        self.assertEqual(r["total"], 30000)
        self.assertEqual(tools.buscar_gastos(texto="super")["cantidad"], 1)

    def test_buscar_invalidos(self):
        self.assertEqual(tools.buscar_gastos(desde="ayer")["status"], "error")
        self.assertEqual(tools.buscar_gastos(desde="2026-12-01", hasta="2026-11-01")["status"], "error")
        self.assertEqual(tools.buscar_gastos(categoria="xyz")["status"], "error")

    # --- resumen_gastos ---
    def test_resumen(self):
        tools.registrar_gasto("Super", 300, "alimentacion", "2026-11-02")
        tools.registrar_gasto("Cine", 100, "ocio", "2026-11-03")
        r = tools.resumen_gastos("2026-11")
        self.assertEqual(r["total"], 400)
        self.assertEqual(r["por_categoria"][0]["categoria"], "alimentacion")
        self.assertEqual(r["por_categoria"][0]["porcentaje"], 75.0)
        self.assertEqual(tools.resumen_gastos("2020-01")["status"], "empty")
        self.assertEqual(tools.resumen_gastos("noviembre")["status"], "error")

    # --- verificar_presupuesto ---
    def test_presupuesto(self):
        tools.registrar_gasto("Super", 900, "alimentacion", "2026-11-02")
        self.assertEqual(tools.verificar_presupuesto(1000, "2026-11")["estado"], "alerta")
        self.assertEqual(tools.verificar_presupuesto(500, "2026-11")["estado"], "excedido")
        self.assertEqual(tools.verificar_presupuesto(5000, "2026-11")["estado"], "dentro")
        self.assertIn("nota", tools.verificar_presupuesto(5000, "2020-01"))
        self.assertEqual(tools.verificar_presupuesto(0, "2026-11")["status"], "error")
        self.assertEqual(tools.verificar_presupuesto(100, "")["status"], "error")

    # --- eliminar_gasto ---
    def test_eliminar(self):
        tools.registrar_gasto("Pan", 1500, "alimentacion", "2026-11-01")
        self.assertEqual(tools.eliminar_gasto(1)["status"], "success")
        self.assertEqual(tools.eliminar_gasto(1)["status"], "error")
        self.assertEqual(tools.eliminar_gasto("abc")["status"], "error")


if __name__ == "__main__":
    unittest.main()
