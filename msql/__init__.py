"""Compilador de MSQL (pseudolenguaje) a PostgreSQL, construido con Lark."""

from .compiler import compilar, construir_ast, parsear
from .errors import MsqlError

__all__ = ["compilar", "construir_ast", "parsear", "MsqlError"]
