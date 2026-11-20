"""Copia los gastos de ejemplo a gestor_gastos/data/gastos.json para probar el agente."""

import shutil
from pathlib import Path

base = Path(__file__).resolve().parent / "gestor_gastos" / "data"
shutil.copy(base / "gastos_ejemplo.json", base / "gastos.json")
print(f"Datos de ejemplo cargados en {base / 'gastos.json'}")
