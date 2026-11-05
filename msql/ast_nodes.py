"""Nodos del Árbol de Sintaxis Abstracta (AST) de MSQL.

El árbol que devuelve Lark (árbol de derivación) contiene detalles de la
gramática que al generar código no importan. El Transformer lo convierte en
estas clases, que representan solo lo esencial de cada instrucción.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


# ---------------------------------------------------------------- Valores

@dataclass
class Literal:
    """Un valor escrito en el programa.

    tipo  : "num", "text" o "bool"
    valor : para num, el texto tal como se escribió (por ejemplo "-1.25");
            para text, el contenido SIN comillas; para bool, True o False.
    """
    tipo: str
    valor: Union[str, bool]


# ------------------------------------------------------------ Condiciones

@dataclass
class Comparacion:
    campo: str
    operador: str          # =, !=, <>, <, >, <=, >=
    valor: Literal


@dataclass
class Logica:
    operador: str          # "AND" u "OR"
    izquierda: "Condicion"
    derecha: "Condicion"


Condicion = Union[Comparacion, Logica]


# ----------------------------------------------------------- Instrucciones

@dataclass
class Columna:
    nombre: str
    tipo: str              # id, num, text, bool, time (en minúscula)
    requerido: bool        # True si el tipo termina en "!"


@dataclass
class Make:
    tabla: str
    columnas: List[Columna]
    linea: int = 0


@dataclass
class Orden:
    campo: str
    direccion: Optional[str] = None   # "ASC", "DESC" o None si no se escribió


@dataclass
class Get:
    tabla: str
    columnas: Optional[List[str]]     # None significa "todas" (ALL)
    donde: Optional[Condicion] = None
    orden: Optional[Orden] = None
    limite: Optional[int] = None
    linea: int = 0


@dataclass
class Asignacion:
    campo: str
    valor: Literal


@dataclass
class Put:
    tabla: str
    asignaciones: List[Asignacion]
    donde: Optional[Condicion] = None  # sin WHERE es INSERT; con WHERE es UPDATE
    linea: int = 0


@dataclass
class Drop:
    tabla: str
    donde: Optional[Condicion] = None  # con WHERE es DELETE; sin WHERE es DROP TABLE
    linea: int = 0


Instruccion = Union[Make, Get, Put, Drop]


@dataclass
class Programa:
    instrucciones: List[Instruccion] = field(default_factory=list)
