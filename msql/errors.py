"""Errores del compilador MSQL."""


class MsqlError(Exception):
    """Error de compilación con posición en el archivo fuente.

    fase: "léxico", "sintáctico" o "semántico" (las fases del compilador
    en las que se puede detectar el error).
    """

    def __init__(self, mensaje, fase, linea=None, columna=None, contexto=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.fase = fase
        self.linea = linea
        self.columna = columna
        self.contexto = contexto      # línea de código con un marcador "^"

    def formatear(self, archivo="<entrada>"):
        posicion = archivo
        if self.linea is not None:
            posicion += f":{self.linea}"
            if self.columna is not None:
                posicion += f":{self.columna}"
        texto = f"{posicion}: error {self.fase}: {self.mensaje}"
        if self.contexto:
            texto += "\n" + self.contexto
        return texto
