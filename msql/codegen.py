"""Generador de código: recorre el AST y produce SQL de PostgreSQL.

El formato de salida sigue los ejemplos de la especificación: CREATE TABLE y
SELECT en varias líneas, cada sentencia termina en punto y coma.
"""

from .ast_nodes import (
    Comparacion, Condicion, Drop, Get, Literal, Logica, Make, Programa, Put,
)

# Tabla 3 de la especificación: tipo del pseudolenguaje -> tipo de PostgreSQL.
TIPOS_POSTGRES = {
    "id": "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
    "num": "NUMERIC",
    "text": "TEXT",
    "bool": "BOOLEAN DEFAULT FALSE",
    "time": "TIMESTAMPTZ DEFAULT NOW()",
}


def generar(programa: Programa) -> str:
    """Devuelve el SQL de todo el programa, una sentencia tras otra."""
    sentencias = [_instruccion(i) for i in programa.instrucciones]
    return "\n".join(sentencias) + ("\n" if sentencias else "")


def _instruccion(nodo) -> str:
    if isinstance(nodo, Make):
        return _make(nodo)
    if isinstance(nodo, Get):
        return _get(nodo)
    if isinstance(nodo, Put):
        return _put(nodo)
    if isinstance(nodo, Drop):
        return _drop(nodo)
    raise TypeError(f"nodo desconocido: {nodo!r}")


# ---------------------------------------------------------------- MAKE

def _make(nodo: Make) -> str:
    lineas = []
    for columna in nodo.columnas:
        definicion = f"{columna.nombre} {TIPOS_POSTGRES[columna.tipo]}"
        if columna.requerido:
            definicion += " NOT NULL"
        lineas.append("  " + definicion)
    cuerpo = ",\n".join(lineas)
    return f"CREATE TABLE {nodo.tabla} (\n{cuerpo}\n);"


# ----------------------------------------------------------------- GET

def _get(nodo: Get) -> str:
    columnas = "*" if nodo.columnas is None else ", ".join(nodo.columnas)
    partes = [f"SELECT {columnas}", f"FROM {nodo.tabla}"]
    if nodo.donde is not None:
        partes.append(f"WHERE {_condicion(nodo.donde)}")
    if nodo.orden is not None:
        orden = f"ORDER BY {nodo.orden.campo}"
        if nodo.orden.direccion:
            orden += f" {nodo.orden.direccion}"
        partes.append(orden)
    if nodo.limite is not None:
        partes.append(f"LIMIT {nodo.limite}")
    return "\n".join(partes) + ";"


# ----------------------------------------------------------------- PUT

def _put(nodo: Put) -> str:
    if nodo.donde is None:
        campos = ", ".join(a.campo for a in nodo.asignaciones)
        valores = ", ".join(_literal(a.valor) for a in nodo.asignaciones)
        return f"INSERT INTO {nodo.tabla} ({campos})\nVALUES ({valores});"
    asignaciones = ", ".join(
        f"{a.campo} = {_literal(a.valor)}" for a in nodo.asignaciones)
    return (f"UPDATE {nodo.tabla}\nSET {asignaciones}\n"
            f"WHERE {_condicion(nodo.donde)};")


# ---------------------------------------------------------------- DROP

def _drop(nodo: Drop) -> str:
    if nodo.donde is None:
        return f"DROP TABLE {nodo.tabla};"
    return f"DELETE FROM {nodo.tabla} WHERE {_condicion(nodo.donde)};"


# ------------------------------------------------- Condiciones y valores

def _condicion(nodo: Condicion) -> str:
    if isinstance(nodo, Comparacion):
        return f"{nodo.campo} {nodo.operador} {_literal(nodo.valor)}"
    if isinstance(nodo, Logica):
        izquierda = _condicion(nodo.izquierda)
        derecha = _condicion(nodo.derecha)
        # AND liga más fuerte que OR: un OR dentro de un AND necesita
        # paréntesis para conservar el significado del programa original.
        if nodo.operador == "AND":
            if _es_or(nodo.izquierda):
                izquierda = f"({izquierda})"
            if _es_or(nodo.derecha):
                derecha = f"({derecha})"
        return f"{izquierda} {nodo.operador} {derecha}"
    raise TypeError(f"condición desconocida: {nodo!r}")


def _es_or(nodo: Condicion) -> bool:
    return isinstance(nodo, Logica) and nodo.operador == "OR"


def _literal(nodo: Literal) -> str:
    if nodo.tipo == "bool":
        return "TRUE" if nodo.valor else "FALSE"
    if nodo.tipo == "text":
        # En PostgreSQL las cadenas llevan comillas simples; una comilla
        # simple dentro del texto se escribe duplicada.
        return "'" + nodo.valor.replace("'", "''") + "'"
    return nodo.valor            # num: se conserva tal como se escribió
