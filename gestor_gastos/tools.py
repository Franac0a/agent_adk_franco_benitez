"""Herramientas del agente de gestión de gastos personales.

Cada herramienta tiene una responsabilidad distinta y devuelve siempre un
diccionario con la clave ``status`` ("success" | "error" | "empty") para que el
modelo pueda interpretar el resultado y responder al usuario sin inventar datos.

Los gastos se guardan en un archivo JSON local (``data/gastos.json``).
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuración y persistencia
# --------------------------------------------------------------------------- #

CATEGORIAS_VALIDAS = [
    "alimentacion",
    "transporte",
    "vivienda",
    "servicios",
    "salud",
    "educacion",
    "ocio",
    "ropa",
    "otros",
]

MONTO_MAXIMO = 10_000_000  # límite de seguridad para detectar errores de tipeo

_DATA_FILE = Path(
    os.getenv(
        "GASTOS_DATA_FILE",
        Path(__file__).resolve().parent / "data" / "gastos.json",
    )
)


def _cargar() -> list[dict]:
    """Lee los gastos del archivo JSON. Devuelve lista vacía si no existe."""
    if not _DATA_FILE.exists():
        return []
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _guardar(gastos: list[dict]) -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(gastos, f, ensure_ascii=False, indent=2)


def _parsear_fecha(texto: str) -> date | None:
    """Convierte 'AAAA-MM-DD' en date. Devuelve None si el formato es inválido."""
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _normalizar_categoria(categoria: str) -> str:
    reemplazos = str.maketrans("áéíóú", "aeiou")
    return categoria.strip().lower().translate(reemplazos)


def _error(mensaje: str) -> dict:
    return {"status": "error", "error_message": mensaje}


# --------------------------------------------------------------------------- #
# Herramienta 1: registrar un gasto
# --------------------------------------------------------------------------- #


def registrar_gasto(descripcion: str, monto: float, categoria: str, fecha: str = "") -> dict:
    """Registra un nuevo gasto personal.

    Args:
        descripcion: Breve descripción del gasto (por ejemplo "Supermercado").
        monto: Importe del gasto en pesos. Debe ser mayor a cero.
        categoria: Una de: alimentacion, transporte, vivienda, servicios, salud,
            educacion, ocio, ropa, otros.
        fecha: Fecha del gasto en formato AAAA-MM-DD. Si se deja vacía se usa
            la fecha de hoy.

    Returns:
        dict con status y el gasto registrado, o un mensaje de error.
    """
    if not descripcion or not str(descripcion).strip():
        return _error("La descripción no puede estar vacía.")

    try:
        monto = float(monto)
    except (TypeError, ValueError):
        return _error(f"El monto '{monto}' no es un número válido.")
    if monto <= 0:
        return _error("El monto debe ser mayor a cero.")
    if monto > MONTO_MAXIMO:
        return _error(f"El monto supera el máximo permitido ({MONTO_MAXIMO}). Verificá el valor.")

    cat = _normalizar_categoria(categoria or "")
    if cat not in CATEGORIAS_VALIDAS:
        return _error(
            f"Categoría '{categoria}' inválida. Categorías válidas: {', '.join(CATEGORIAS_VALIDAS)}."
        )

    if fecha and fecha.strip():
        f = _parsear_fecha(fecha)
        if f is None:
            return _error(f"La fecha '{fecha}' no tiene el formato AAAA-MM-DD.")
        if f > date.today():
            return _error("No se pueden registrar gastos con fecha futura.")
    else:
        f = date.today()

    gastos = _cargar()
    nuevo_id = max((g["id"] for g in gastos), default=0) + 1
    gasto = {
        "id": nuevo_id,
        "descripcion": descripcion.strip(),
        "monto": round(monto, 2),
        "categoria": cat,
        "fecha": f.isoformat(),
    }
    gastos.append(gasto)
    _guardar(gastos)
    return {"status": "success", "gasto": gasto}


# --------------------------------------------------------------------------- #
# Herramienta 2: buscar / listar gastos
# --------------------------------------------------------------------------- #


def buscar_gastos(categoria: str = "", desde: str = "", hasta: str = "", texto: str = "") -> dict:
    """Busca gastos registrados aplicando filtros opcionales.

    Args:
        categoria: Filtra por categoría (vacío = todas).
        desde: Fecha inicial inclusive, formato AAAA-MM-DD (vacío = sin límite).
        hasta: Fecha final inclusive, formato AAAA-MM-DD (vacío = sin límite).
        texto: Texto a buscar dentro de la descripción (vacío = sin filtro).

    Returns:
        dict con status, la lista de gastos encontrados, la cantidad y el total.
    """
    cat = _normalizar_categoria(categoria) if categoria else ""
    if cat and cat not in CATEGORIAS_VALIDAS:
        return _error(
            f"Categoría '{categoria}' inválida. Categorías válidas: {', '.join(CATEGORIAS_VALIDAS)}."
        )

    f_desde = _parsear_fecha(desde) if desde else None
    if desde and f_desde is None:
        return _error(f"La fecha 'desde' ('{desde}') no tiene el formato AAAA-MM-DD.")
    f_hasta = _parsear_fecha(hasta) if hasta else None
    if hasta and f_hasta is None:
        return _error(f"La fecha 'hasta' ('{hasta}') no tiene el formato AAAA-MM-DD.")
    if f_desde and f_hasta and f_desde > f_hasta:
        return _error("La fecha 'desde' no puede ser posterior a la fecha 'hasta'.")

    resultado = []
    for g in _cargar():
        fg = _parsear_fecha(g.get("fecha", ""))
        if cat and g.get("categoria") != cat:
            continue
        if f_desde and (fg is None or fg < f_desde):
            continue
        if f_hasta and (fg is None or fg > f_hasta):
            continue
        if texto and texto.strip().lower() not in g.get("descripcion", "").lower():
            continue
        resultado.append(g)

    if not resultado:
        return {
            "status": "empty",
            "message": "No se encontraron gastos con los filtros indicados.",
            "gastos": [],
            "cantidad": 0,
            "total": 0,
        }

    resultado.sort(key=lambda g: g["fecha"])
    return {
        "status": "success",
        "gastos": resultado,
        "cantidad": len(resultado),
        "total": round(sum(g["monto"] for g in resultado), 2),
    }


# --------------------------------------------------------------------------- #
# Herramienta 3: resumen estadístico
# --------------------------------------------------------------------------- #


def resumen_gastos(mes: str = "") -> dict:
    """Genera un resumen de gastos agrupados por categoría.

    Args:
        mes: Mes a resumir en formato AAAA-MM (por ejemplo "2026-11").
            Si se deja vacío se resumen todos los gastos registrados.

    Returns:
        dict con status, total general, cantidad de gastos, total y porcentaje
        por categoría, gasto más alto y promedio por gasto.
    """
    gastos = _cargar()
    if mes:
        try:
            datetime.strptime(mes.strip(), "%Y-%m")
        except ValueError:
            return _error(f"El mes '{mes}' no tiene el formato AAAA-MM.")
        gastos = [g for g in gastos if g.get("fecha", "").startswith(mes.strip())]

    if not gastos:
        periodo = f"el mes {mes}" if mes else "ningún período"
        return {"status": "empty", "message": f"No hay gastos registrados para {periodo}."}

    total = sum(g["monto"] for g in gastos)
    por_categoria: dict[str, float] = {}
    for g in gastos:
        por_categoria[g["categoria"]] = por_categoria.get(g["categoria"], 0) + g["monto"]

    detalle = [
        {
            "categoria": c,
            "total": round(m, 2),
            "porcentaje": round(m * 100 / total, 1),
        }
        for c, m in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)
    ]
    mayor = max(gastos, key=lambda g: g["monto"])

    return {
        "status": "success",
        "periodo": mes or "todos",
        "total": round(total, 2),
        "cantidad": len(gastos),
        "promedio": round(total / len(gastos), 2),
        "por_categoria": detalle,
        "gasto_mas_alto": mayor,
    }


# --------------------------------------------------------------------------- #
# Herramienta 4: controlar presupuesto
# --------------------------------------------------------------------------- #


def verificar_presupuesto(presupuesto: float, mes: str, categoria: str = "") -> dict:
    """Compara lo gastado en un mes contra un presupuesto.

    Args:
        presupuesto: Monto máximo que el usuario planea gastar. Debe ser > 0.
        mes: Mes a evaluar en formato AAAA-MM.
        categoria: Si se indica, compara solo los gastos de esa categoría.

    Returns:
        dict con status, gastado, disponible, porcentaje usado y un estado
        ("dentro", "alerta" si se usó 80% o más, "excedido").
    """
    try:
        presupuesto = float(presupuesto)
    except (TypeError, ValueError):
        return _error(f"El presupuesto '{presupuesto}' no es un número válido.")
    if presupuesto <= 0:
        return _error("El presupuesto debe ser mayor a cero.")

    if not mes:
        return _error("Debés indicar el mes en formato AAAA-MM.")
    try:
        datetime.strptime(mes.strip(), "%Y-%m")
    except ValueError:
        return _error(f"El mes '{mes}' no tiene el formato AAAA-MM.")

    cat = _normalizar_categoria(categoria) if categoria else ""
    if cat and cat not in CATEGORIAS_VALIDAS:
        return _error(
            f"Categoría '{categoria}' inválida. Categorías válidas: {', '.join(CATEGORIAS_VALIDAS)}."
        )

    gastos = [
        g
        for g in _cargar()
        if g.get("fecha", "").startswith(mes.strip()) and (not cat or g["categoria"] == cat)
    ]
    gastado = round(sum(g["monto"] for g in gastos), 2)
    porcentaje = round(gastado * 100 / presupuesto, 1)

    if porcentaje > 100:
        estado = "excedido"
    elif porcentaje >= 80:
        estado = "alerta"
    else:
        estado = "dentro"

    respuesta = {
        "status": "success",
        "mes": mes,
        "categoria": cat or "todas",
        "presupuesto": round(presupuesto, 2),
        "gastado": gastado,
        "disponible": round(presupuesto - gastado, 2),
        "porcentaje_usado": porcentaje,
        "estado": estado,
        "cantidad_gastos": len(gastos),
    }
    if not gastos:
        respuesta["nota"] = "No hay gastos registrados en ese período; todo el presupuesto está disponible."
    return respuesta


# --------------------------------------------------------------------------- #
# Herramienta 5: eliminar un gasto
# --------------------------------------------------------------------------- #


def eliminar_gasto(gasto_id: int) -> dict:
    """Elimina un gasto registrado a partir de su identificador.

    Args:
        gasto_id: Número de identificación (id) del gasto a eliminar.

    Returns:
        dict con status y el gasto eliminado, o un mensaje de error si no existe.
    """
    try:
        gasto_id = int(gasto_id)
    except (TypeError, ValueError):
        return _error(f"El id '{gasto_id}' no es un número entero válido.")
    if gasto_id <= 0:
        return _error("El id debe ser un número positivo.")

    gastos = _cargar()
    for i, g in enumerate(gastos):
        if g["id"] == gasto_id:
            eliminado = gastos.pop(i)
            _guardar(gastos)
            return {"status": "success", "gasto_eliminado": eliminado}
    return _error(f"No existe ningún gasto con id {gasto_id}.")
