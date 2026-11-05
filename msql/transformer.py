"""Transformer: convierte el árbol de derivación de Lark en el AST de MSQL.

Lark llama a un método por cada regla de la gramática, con el mismo nombre
(o con el nombre del alias "-> alias"). Cada método recibe la lista de hijos
ya transformados y devuelve el valor que representa a ese nodo. El recorrido
es de abajo hacia arriba, así que esto es traducción dirigida por sintaxis
con atributos sintetizados.
"""

from lark import Transformer, Token

from .ast_nodes import (
    Asignacion, Columna, Comparacion, Drop, Get, Literal, Logica, Make,
    Orden, Programa, Put,
)


def _quitar_comillas(texto: str) -> str:
    # Quita las comillas de la cadena y deshace la comilla duplicada:
    #   'it''s'  ->  it's        "di ""hola"""  ->  di "hola"
    comilla = texto[0]
    return texto[1:-1].replace(comilla * 2, comilla)


class MsqlTransformer(Transformer):
    # Programa y envoltura -------------------------------------------------
    def start(self, hijos):
        return Programa(instrucciones=list(hijos))

    def instruccion(self, hijos):
        return hijos[0]

    # MAKE -----------------------------------------------------------------
    def make(self, hijos):
        tabla, *columnas = hijos
        return Make(tabla=str(tabla), columnas=columnas, linea=tabla.line)

    def campo(self, hijos):
        nombre, (tipo, requerido) = hijos
        return Columna(nombre=str(nombre), tipo=tipo, requerido=requerido)

    def tipo(self, hijos):
        tipo, requerido = hijos          # requerido es el token "!" o None
        return str(tipo).lower(), requerido is not None

    # GET ------------------------------------------------------------------
    def todas_columnas(self, hijos):
        return None                      # None significa "todas las columnas"

    def lista_columnas(self, hijos):
        return [str(nombre) for nombre in hijos]

    def get(self, hijos):
        columnas, tabla, donde, orden, limite = hijos
        return Get(tabla=str(tabla), columnas=columnas, donde=donde,
                   orden=orden, limite=limite, linea=tabla.line)

    def orden(self, hijos):
        campo, direccion = hijos
        return Orden(campo=str(campo),
                     direccion=str(direccion).upper() if direccion else None)

    def limite(self, hijos):
        return int(hijos[0])

    # PUT ------------------------------------------------------------------
    def asignacion(self, hijos):
        campo, valor = hijos
        return Asignacion(campo=str(campo), valor=valor)

    def put(self, hijos):
        tabla, *resto = hijos
        *asignaciones, donde = resto     # el último hijo es el WHERE o None
        return Put(tabla=str(tabla), asignaciones=asignaciones, donde=donde,
                   linea=tabla.line)

    # DROP -----------------------------------------------------------------
    def drop(self, hijos):
        tabla, donde = hijos
        return Drop(tabla=str(tabla), donde=donde, linea=tabla.line)

    # Condiciones ----------------------------------------------------------
    def donde(self, hijos):
        return hijos[0]

    def o_logico(self, hijos):
        izquierda, derecha = hijos
        return Logica("OR", izquierda, derecha)

    def y_logico(self, hijos):
        izquierda, derecha = hijos
        return Logica("AND", izquierda, derecha)

    def comparacion(self, hijos):
        campo, operador, valor = hijos
        return Comparacion(campo=str(campo), operador=str(operador), valor=valor)

    # Valores --------------------------------------------------------------
    def numero(self, hijos):
        return Literal("num", str(hijos[0]))

    def cadena(self, hijos):
        return Literal("text", _quitar_comillas(str(hijos[0])))

    def verdadero(self, hijos):
        return Literal("bool", True)

    def falso(self, hijos):
        return Literal("bool", False)
