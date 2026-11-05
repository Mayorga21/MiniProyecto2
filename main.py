"""Interfaz de línea de comandos del compilador MSQL.

Ejemplos:
    python main.py examples/schema.msql          genera examples/schema.sql
    python main.py examples                      compila todos los .msql de la carpeta
    python main.py examples/*.msql -o salida     deja los .sql en la carpeta salida
    python main.py examples/queries.msql --stdout
    python main.py examples/queries.msql --tree  muestra el árbol de derivación
    python main.py examples/queries.msql --ast   muestra el AST
"""

import argparse
import glob
import sys
from pathlib import Path
from pprint import pformat

from msql import MsqlError, compilar, construir_ast, parsear


def _expandir(entradas):
    """Convierte carpetas y comodines en una lista de archivos .msql.

    Se hace aquí y no en la terminal porque Windows (cmd y PowerShell) no
    expande comodines como *.msql por su cuenta.
    """
    archivos = []
    for entrada in entradas:
        ruta = Path(entrada)
        if ruta.is_dir():
            archivos.extend(sorted(ruta.glob("*.msql")))
        elif any(c in entrada for c in "*?["):
            archivos.extend(Path(p) for p in sorted(glob.glob(entrada)))
        else:
            archivos.append(ruta)
    return archivos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compila MSQL (pseudolenguaje) a SQL de PostgreSQL.")
    ap.add_argument("entradas", nargs="+",
                    help="archivos .msql, carpetas o comodines")
    ap.add_argument("-o", "--salida", metavar="CARPETA",
                    help="carpeta donde escribir los .sql "
                         "(por defecto, junto a cada archivo fuente)")
    ap.add_argument("--stdout", action="store_true",
                    help="imprime el SQL en pantalla en vez de escribir archivos")
    ap.add_argument("--tree", action="store_true",
                    help="imprime el árbol de derivación de Lark")
    ap.add_argument("--ast", action="store_true",
                    help="imprime el AST")
    args = ap.parse_args(argv)

    # La consola de Windows puede usar una codificación que no es UTF-8.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    archivos = _expandir(args.entradas)
    if not archivos:
        print("No se encontraron archivos .msql.", file=sys.stderr)
        return 1

    errores = 0
    for archivo in archivos:
        try:
            texto = archivo.read_text(encoding="utf-8-sig")
        except OSError as e:
            print(f"{archivo}: no se pudo leer ({e.strerror})", file=sys.stderr)
            errores += 1
            continue

        try:
            if args.tree:
                print(parsear(texto).pretty())
            if args.ast:
                print(pformat(construir_ast(texto), width=100))
            sql = compilar(texto)
        except MsqlError as e:
            print(e.formatear(str(archivo)), file=sys.stderr)
            errores += 1
            continue

        if args.stdout:
            print(f"-- {archivo.name}")
            print(sql, end="")
            continue

        carpeta = Path(args.salida) if args.salida else archivo.parent
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / (archivo.stem + ".sql")
        destino.write_text(sql, encoding="utf-8", newline="\n")
        print(f"{archivo} -> {destino}")

    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
