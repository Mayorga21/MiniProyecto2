"""Fachada del compilador: une las fases en una sola función.

    texto MSQL -> [lexer + parser (Lark)] -> árbol de derivación
               -> [MsqlTransformer]       -> AST
               -> [semantic.analizar]     -> AST validado
               -> [codegen.generar]       -> texto SQL
"""

from pathlib import Path

from lark import Lark
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedToken

from . import semantic
from .ast_nodes import Programa
from .codegen import generar
from .errors import MsqlError
from .transformer import MsqlTransformer

_RUTA_GRAMATICA = Path(__file__).with_name("grammar.lark")

# LALR(1) con lexer contextual (el valor por defecto de Lark para LALR).
# propagate_positions=True guarda línea y columna en cada nodo del árbol.
_parser = Lark(
    _RUTA_GRAMATICA.read_text(encoding="utf-8"),
    parser="lalr",
    propagate_positions=True,
)

# Nombres legibles para los terminales que Lark nombra internamente.
_NOMBRES_TERMINALES = {
    "$END": "fin del archivo",
    "_NL": "fin de línea",
    "LPAR": "'('",
    "RPAR": "')'",
    "COMMA": "','",
    "EQUAL": "'='",
    "NAME": "un identificador",
    "TIPO": "un tipo (id, num, text, bool, time)",
    "REQUERIDO": "'!'",
    "DIRECCION": "ASC o DESC",
    "OPERADOR": "un operador de comparación",
    "NUMERO": "un número",
    "ENTERO": "un número entero",
    "CADENA": "una cadena entre comillas",
}


def _nombre(terminal: str) -> str:
    if terminal in _NOMBRES_TERMINALES:
        return _NOMBRES_TERMINALES[terminal]
    return terminal.lstrip("_")        # _FROM -> FROM


def _contexto(texto: str, linea: int, columna: int) -> str:
    lineas = texto.splitlines()
    if not (1 <= linea <= len(lineas)):
        return ""
    return f"  {lineas[linea - 1]}\n  {' ' * (columna - 1)}^"


def parsear(texto: str):
    """Fases léxica y sintáctica: devuelve el árbol de derivación de Lark."""
    if not texto.endswith("\n"):
        texto += "\n"                  # la gramática exige que toda línea termine en _NL
    try:
        return _parser.parse(texto)
    except UnexpectedCharacters as e:
        raise MsqlError(
            f"carácter no reconocido {e.char!r}", "léxico",
            e.line, e.column, _contexto(texto, e.line, e.column)) from None
    except UnexpectedToken as e:
        esperado = sorted({_nombre(t) for t in e.expected})
        encontrado = _nombre(e.token.type) if e.token.type in (
            "$END", "_NL") else repr(str(e.token))
        raise MsqlError(
            f"se encontró {encontrado} pero se esperaba: {', '.join(esperado)}",
            "sintáctico", e.line, e.column,
            _contexto(texto, e.line, e.column)) from None
    except UnexpectedEOF:
        raise MsqlError("la entrada terminó antes de completar la instrucción",
                        "sintáctico") from None


def construir_ast(texto: str) -> Programa:
    """Parsea y transforma el texto en un AST validado semánticamente."""
    programa = MsqlTransformer().transform(parsear(texto))
    semantic.analizar(programa)
    return programa


def compilar(texto: str) -> str:
    """Compila texto MSQL y devuelve el SQL de PostgreSQL."""
    return generar(construir_ast(texto))
