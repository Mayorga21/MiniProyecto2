# Compilador MSQL a PostgreSQL

Compilador escrito en Python con la biblioteca Lark. Traduce un pseudolenguaje
orientado a líneas (archivos `.msql`) a SQL de PostgreSQL. Proyecto del curso
IS-581 Compiladores e Intérpretes (UNADECA).

Ejemplo:

```
GET name, email FROM users WHERE name = 'Alex' SORT created TOP 5
```

se compila a

```sql
SELECT name, email
FROM users
WHERE name = 'Alex'
ORDER BY created
LIMIT 5;
```

## Requisitos

Python 3.9 o superior y pip. Lark es la única dependencia en tiempo de ejecución.

## Instalación

Windows (PowerShell):

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell bloquea la activación, ejecute una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, o use `cmd` y
`.venv\Scripts\activate.bat`.

Linux o macOS:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```
python main.py examples/schema.msql        escribe examples/schema.sql
python main.py examples                    compila todos los .msql de la carpeta
python main.py "examples/*.msql" -o salida deja los .sql en la carpeta salida
python main.py examples/queries.msql --stdout   imprime el SQL en pantalla
python main.py examples/queries.msql --tree     imprime el árbol de derivación de Lark
python main.py examples/queries.msql --ast      imprime el AST
```

En Linux use `python3` en lugar de `python` si hace falta. Los archivos
`examples/*.sql` incluidos en el repositorio son el resultado de compilar los
seis ejemplos.

Si hay un error, el compilador indica archivo, línea, columna y la fase en que
se detectó, y termina con código de salida 1:

```
examples/malo.msql:2:9: error sintáctico: se encontró 'users' pero se esperaba: FROM
  GET ALL users
          ^
```

## Estructura del proyecto

```
main.py                 interfaz de línea de comandos (el driver)
msql/
  grammar.lark          gramática: lexer y parser (análisis léxico y sintáctico)
  ast_nodes.py          clases del árbol de sintaxis abstracta
  transformer.py        árbol de Lark -> AST (traducción dirigida por sintaxis)
  semantic.py           análisis semántico
  codegen.py            AST -> SQL de PostgreSQL
  compiler.py           une las fases y traduce los errores de Lark
  errors.py             MsqlError
examples/               archivos .msql de prueba y el .sql que generan
tests/test_compiler.py  pruebas automáticas
```

## Cómo funciona

```
texto MSQL -> lexer y parser (Lark) -> árbol de derivación
           -> MsqlTransformer        -> AST
           -> semantic.analizar      -> AST validado
           -> codegen.generar        -> texto SQL
```

1. Análisis léxico y sintáctico. Lark lee `grammar.lark` y construye un parser
   LALR(1) con lexer contextual. El lexer contextual solo busca los tokens que
   el parser acepta en ese punto, y eso permite que `id` sea a la vez un tipo
   (`id id`) y un nombre de campo, o que `all` sea la palabra clave en
   `GET all FROM t` pero `allowance` sea un identificador.
2. Árbol de derivación. Lark lo construye solo a partir de la gramática. Los
   terminales que empiezan con guion bajo (`_FROM`, `_NL`) se reconocen pero no
   aparecen en el árbol.
3. AST. `MsqlTransformer` tiene un método por regla; cada uno recibe sus hijos
   ya convertidos y devuelve un nodo de `ast_nodes.py`. Por ejemplo,
   `comparacion` devuelve un `Comparacion(campo, operador, valor)`.
4. Análisis semántico. Revisa lo que una gramática libre de contexto no puede
   expresar: columnas repetidas en un MAKE, más de una columna `id` y campos
   asignados dos veces en un PUT.
5. Generación de código. `codegen.py` recorre el AST y produce el SQL, con el
   mapeo de tipos de la especificación.

### Precedencia de las condiciones

La gramática tiene un nivel de regla por nivel de precedencia:

```
?condicion:  condicion _OR conjuncion    -> o_logico
           | conjuncion
?conjuncion: conjuncion _AND primaria    -> y_logico
           | primaria
```

AND queda más abajo en el árbol, por lo que liga más fuerte que OR, y la
recursión por la izquierda da asociatividad izquierda. Al generar SQL, un OR
dentro de un AND se escribe entre paréntesis para no cambiar el significado.

## Decisiones de diseño

La especificación y los ejemplos no cubren algunos casos. Estas son las
interpretaciones tomadas:

1. `GET ALL FROM t` se traduce a `SELECT *`.
2. `SORT campo DESC` y `SORT campo ASC` se traducen a `ORDER BY campo DESC` y
   `ORDER BY campo ASC`. Sin dirección se omite.
3. Las cadenas pueden escribirse con comillas simples o dobles, pero siempre se
   emiten con comillas simples, porque en PostgreSQL las comillas dobles
   designan identificadores. Una comilla repetida dentro de la cadena
   (`'it''s'`) es una comilla literal.
4. Los operadores `=`, `!=`, `<>`, `<`, `>`, `<=` y `>=` se emiten tal como se
   escribieron; PostgreSQL acepta `!=` y `<>`.
5. Las palabras clave y los tipos no distinguen mayúsculas de minúsculas
   (ejemplo `keyword-case.msql`). Los nombres de tablas y campos se conservan
   exactamente como se escribieron.
6. Los booleanos `true` y `false` se emiten como `TRUE` y `FALSE`.
7. Los números se emiten tal como se escribieron (`12.50` se mantiene `12.50`).
8. Se permiten paréntesis en las condiciones. No están en la especificación; se
   agregaron para poder expresar `(a OR b) AND c`.
9. El signo `!` se agrega al final de la definición, después del DEFAULT, por
   ejemplo `BOOLEAN DEFAULT FALSE NOT NULL`. En una columna `id!` el NOT NULL es
   redundante con PRIMARY KEY pero válido.
10. Las sentencias generadas se separan con un salto de línea, como en el
    ejemplo 5 de la especificación.
11. Los nombres no se entrecomillan en la salida; un campo cuyo nombre sea
    palabra reservada de PostgreSQL (por ejemplo `order`) produciría SQL
    inválido.
12. Las líneas en blanco se ignoran, y una instrucción no puede continuar en la
    línea siguiente (el lenguaje es orientado a líneas).

## Pruebas

```
pip install -r requirements-dev.txt
python -m pytest -v
```

Las pruebas cubren los cinco ejemplos de la especificación con su salida
exacta, el mapeo de tipos, las palabras clave en distintos casos, la
precedencia, las comillas, los errores de cada fase y los seis archivos de
`examples/`. Si `pglast` está instalado (opcional), las pruebas además validan
que el SQL generado sea sintácticamente válido con el parser de PostgreSQL;
si no, esas pruebas se omiten.

## Referencias

Shinan, E. (s. f.). Lark documentation. https://lark-parser.readthedocs.io

Aho, A. V., Lam, M. S., Sethi, R. y Ullman, J. D. (2008). Compiladores:
principios, técnicas y herramientas (2.ª ed.). Pearson.
# MiniProyecto2
