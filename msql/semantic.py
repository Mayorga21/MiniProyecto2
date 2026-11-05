"""Análisis semántico de MSQL.

La gramática solo garantiza que las instrucciones tengan la forma correcta.
Aquí se revisan reglas que una gramática libre de contexto no puede expresar:

  1. En un MAKE no puede haber dos columnas con el mismo nombre.
  2. En un MAKE solo puede haber una columna de tipo id, porque id se traduce
     a PRIMARY KEY y una tabla tiene una sola llave primaria.
  3. En un PUT no se puede asignar el mismo campo dos veces.
"""

from .ast_nodes import Make, Programa, Put
from .errors import MsqlError


def analizar(programa: Programa) -> None:
    for instruccion in programa.instrucciones:
        if isinstance(instruccion, Make):
            _revisar_make(instruccion)
        elif isinstance(instruccion, Put):
            _revisar_put(instruccion)


def _revisar_make(make: Make) -> None:
    vistos = set()
    ids = 0
    for columna in make.columnas:
        if columna.nombre in vistos:
            raise MsqlError(
                f"la columna '{columna.nombre}' está repetida en la tabla "
                f"'{make.tabla}'", "semántico", linea=make.linea)
        vistos.add(columna.nombre)
        if columna.tipo == "id":
            ids += 1
    if ids > 1:
        raise MsqlError(
            f"la tabla '{make.tabla}' tiene {ids} columnas de tipo id; "
            "solo puede haber una llave primaria", "semántico",
            linea=make.linea)


def _revisar_put(put: Put) -> None:
    vistos = set()
    for asignacion in put.asignaciones:
        if asignacion.campo in vistos:
            raise MsqlError(
                f"el campo '{asignacion.campo}' se asigna más de una vez "
                f"en PUT {put.tabla}", "semántico", linea=put.linea)
        vistos.add(asignacion.campo)
