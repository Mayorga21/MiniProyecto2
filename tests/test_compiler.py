"""Pruebas del compilador MSQL.

Ejecutar con:  python -m pytest -v
"""

from pathlib import Path

import pytest

from msql import MsqlError, compilar, construir_ast
from msql.ast_nodes import Comparacion, Logica

EJEMPLOS = Path(__file__).resolve().parent.parent / "examples"


# ---------------------------------------------------------------------------
# Los 5 ejemplos completos de la especificación (sección 5 del PDF)
# ---------------------------------------------------------------------------

def test_ejemplo1_make():
    fuente = "MAKE users (id id, name text, email text!, created time)"
    esperado = (
        "CREATE TABLE users (\n"
        "  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "  name TEXT,\n"
        "  email TEXT NOT NULL,\n"
        "  created TIMESTAMPTZ DEFAULT NOW()\n"
        ");\n"
    )
    assert compilar(fuente) == esperado


def test_ejemplo2_insert():
    fuente = "PUT users (name = 'Alex', email = 'alex@test.com')"
    esperado = ("INSERT INTO users (name, email)\n"
                "VALUES ('Alex', 'alex@test.com');\n")
    assert compilar(fuente) == esperado


def test_ejemplo3_select():
    fuente = "GET name, email FROM users WHERE name = 'Alex' SORT created TOP 5"
    esperado = ("SELECT name, email\n"
                "FROM users\n"
                "WHERE name = 'Alex'\n"
                "ORDER BY created\n"
                "LIMIT 5;\n")
    assert compilar(fuente) == esperado


def test_ejemplo4_update():
    fuente = "PUT users (name = 'Alexander') WHERE email = 'alex@test.com'"
    esperado = ("UPDATE users\n"
                "SET name = 'Alexander'\n"
                "WHERE email = 'alex@test.com';\n")
    assert compilar(fuente) == esperado


def test_ejemplo5_delete_y_drop_table():
    fuente = "DROP users WHERE name = 'Alex'\nDROP users"
    esperado = ("DELETE FROM users WHERE name = 'Alex';\n"
                "DROP TABLE users;\n")
    assert compilar(fuente) == esperado


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tipo, sql", [
    ("id", "BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"),
    ("num", "NUMERIC"),
    ("text", "TEXT"),
    ("bool", "BOOLEAN DEFAULT FALSE"),
    ("time", "TIMESTAMPTZ DEFAULT NOW()"),
])
def test_mapeo_de_tipos(tipo, sql):
    assert f"c {sql}\n" in compilar(f"MAKE t (c {tipo})")


@pytest.mark.parametrize("tipo, sql", [
    ("num!", "NUMERIC NOT NULL"),
    ("text!", "TEXT NOT NULL"),
    ("bool!", "BOOLEAN DEFAULT FALSE NOT NULL"),
    ("time!", "TIMESTAMPTZ DEFAULT NOW() NOT NULL"),
])
def test_signo_de_exclamacion_agrega_not_null(tipo, sql):
    assert f"c {sql}\n" in compilar(f"MAKE t (c {tipo})")


def test_un_campo_puede_llamarse_igual_que_su_tipo():
    # "id id": el primero es el nombre y el segundo el tipo.
    assert "id BIGINT" in compilar("MAKE t (id id)")


# ---------------------------------------------------------------------------
# Palabras clave sin distinguir mayúsculas
# ---------------------------------------------------------------------------

def test_palabras_clave_en_minuscula_y_mixtas():
    minus = compilar("get ALL from t sort a top 3")
    mayus = compilar("GET ALL FROM t SORT a TOP 3")
    mixta = compilar("Get all From t Sort a Top 3")
    assert minus == mayus == mixta
    assert minus.startswith("SELECT *\n")


def test_los_identificadores_si_distinguen_mayusculas():
    assert "FROM Users;" in compilar("GET ALL FROM Users")


def test_identificador_que_empieza_como_palabra_clave():
    # "allowance" no debe leerse como ALL + "owance".
    assert "SELECT allowance\n" in compilar("GET allowance FROM t")


# ---------------------------------------------------------------------------
# Condiciones
# ---------------------------------------------------------------------------

def test_and_liga_mas_fuerte_que_or():
    arbol = construir_ast("GET ALL FROM t WHERE a = 1 OR b = 2 AND c = 3")
    donde = arbol.instrucciones[0].donde
    assert isinstance(donde, Logica) and donde.operador == "OR"
    assert isinstance(donde.izquierda, Comparacion)
    assert isinstance(donde.derecha, Logica) and donde.derecha.operador == "AND"


def test_asociatividad_izquierda():
    arbol = construir_ast("GET ALL FROM t WHERE a = 1 AND b = 2 AND c = 3")
    donde = arbol.instrucciones[0].donde
    assert isinstance(donde.izquierda, Logica)       # (a AND b) AND c
    assert isinstance(donde.derecha, Comparacion)


def test_parentesis_cambian_la_precedencia():
    sql = compilar("GET ALL FROM t WHERE (a = 1 OR b = 2) AND c = 3")
    assert "WHERE (a = 1 OR b = 2) AND c = 3;" in sql


def test_no_se_agregan_parentesis_innecesarios():
    sql = compilar("GET ALL FROM t WHERE a = 1 OR b = 2 AND c = 3")
    assert "WHERE a = 1 OR b = 2 AND c = 3;" in sql


@pytest.mark.parametrize("op", ["=", "!=", "<>", "<", ">", "<=", ">="])
def test_operadores_de_comparacion(op):
    assert f"WHERE a {op} 1;" in compilar(f"GET ALL FROM t WHERE a {op} 1")


# ---------------------------------------------------------------------------
# Valores
# ---------------------------------------------------------------------------

def test_comillas_dobles_se_convierten_a_simples():
    # En PostgreSQL las comillas dobles son identificadores, no cadenas.
    assert "WHERE e = 'x@y.com';" in compilar('GET ALL FROM t WHERE e = "x@y.com"')


def test_comilla_simple_dentro_de_cadena():
    assert "VALUES ('it''s');" in compilar("PUT t (s = 'it''s')")
    assert "VALUES ('it''s');" in compilar('PUT t (s = "it\'s")')


def test_numeros_negativos_y_decimales():
    assert "SET p = -1.25\n" in compilar("PUT t (p = -1.25) WHERE a = 1")
    assert "VALUES (12.50);" in compilar("PUT t (p = 12.50)")


def test_booleanos():
    assert "VALUES (TRUE, FALSE);" in compilar("PUT t (a = true, b = FALSE)")


def test_desc_y_asc():
    assert "ORDER BY a DESC" in compilar("GET ALL FROM t SORT a DESC")
    assert "ORDER BY a ASC" in compilar("GET ALL FROM t SORT a asc")


# ---------------------------------------------------------------------------
# Formato del archivo
# ---------------------------------------------------------------------------

def test_lineas_en_blanco_y_final_sin_salto():
    assert compilar("\n\nDROP t\n\n\nDROP u") == "DROP TABLE t;\nDROP TABLE u;\n"


def test_saltos_de_linea_windows():
    assert compilar("DROP t\r\nDROP u\r\n") == "DROP TABLE t;\nDROP TABLE u;\n"


def test_archivo_vacio():
    assert compilar("") == ""
    assert compilar("\n\n") == ""


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

def test_error_lexico():
    with pytest.raises(MsqlError) as e:
        compilar("DROP t WHERE a = $")
    assert e.value.fase == "léxico" and e.value.linea == 1


def test_error_sintactico_con_posicion():
    with pytest.raises(MsqlError) as e:
        compilar("DROP t\nGET ALL users")
    assert e.value.fase == "sintáctico"
    assert e.value.linea == 2
    assert "FROM" in e.value.mensaje


def test_una_instruccion_no_continua_en_la_linea_siguiente():
    with pytest.raises(MsqlError):
        compilar("GET ALL\nFROM t")


def test_error_por_instruccion_desconocida():
    with pytest.raises(MsqlError) as e:
        compilar("SELECT * FROM t")
    assert e.value.fase == "sintáctico"


def test_error_semantico_columna_repetida():
    with pytest.raises(MsqlError) as e:
        compilar("MAKE t (a text, a num)")
    assert e.value.fase == "semántico"


def test_error_semantico_dos_llaves_primarias():
    with pytest.raises(MsqlError):
        compilar("MAKE t (a id, b id)")


def test_error_semantico_campo_asignado_dos_veces():
    with pytest.raises(MsqlError):
        compilar("PUT t (a = 1, a = 2)")


# ---------------------------------------------------------------------------
# Los archivos de la carpeta examples/
# ---------------------------------------------------------------------------

ARCHIVOS = sorted(EJEMPLOS.glob("*.msql"))


def test_hay_ejemplos():
    assert len(ARCHIVOS) == 6


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_los_ejemplos_compilan(archivo):
    sql = compilar(archivo.read_text(encoding="utf-8"))
    assert sql.strip().endswith(";")


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_el_sql_generado_es_valido_en_postgresql(archivo):
    """Valida con el parser real de PostgreSQL (pglast), si está instalado."""
    pglast = pytest.importorskip("pglast")
    sql = compilar(archivo.read_text(encoding="utf-8"))
    pglast.parse_sql(sql)       # lanza una excepción si la sintaxis es inválida
