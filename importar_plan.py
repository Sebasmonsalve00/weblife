# ============================================================
#  importar_plan.py - Leer TU documento con fechas y horas
#
#  Para un Excel o CSV propio (un plan de estudio, entregas, entrenos...)
#  donde cada cosa tiene un día concreto. Cada cosa va a TU calendario
#  y, si tiene hora, sale también en el horario la semana que le toca.
#  (No hace falta poner universidad, carrera ni año: eso es solo para
#  los calendarios oficiales de "Añade tus eventos".)
#
#  Entiende dos formas de tabla:
#   1. Una fila por cosa:   fecha | hora (o desde/hasta) | qué | lugar
#      Si la fecha está vacía, vale la de la fila de arriba (celdas combinadas).
#   2. Cuadrícula: arriba los días ("Lunes 1/12", "02/12/2026"...),
#      a la izquierda las horas ("9:00 - 11:00") y en cada casilla qué haces.
#
#  Devuelve la misma lista que lee una foto (ver leer_imagen.limpiar_cosas):
#  [{"nombre", "fecha", "dia", "hora_inicio", "hora_fin", "lugar", "tipo"}]
# ============================================================

import re
from datetime import date, datetime

from importar_eventos import MESES, hojas_del_archivo, leer_fecha, sin_tildes
from importar_horario import leer_rango

# Cómo puede llamarse cada columna en la fila de títulos
TITULOS = {
    "fecha": ("fecha", "dia", "date", "cuando", "jornada"),
    "hora": ("hora", "horas", "horario", "franja", "time"),
    "desde": ("desde", "inicio", "hora inicio", "hora de inicio", "empieza", "comienza", "start"),
    "hasta": ("hasta", "fin", "hora fin", "hora de fin", "hora final", "termina", "end"),
    "nombre": ("nombre", "evento", "asignatura", "materia", "tema", "actividad", "que", "que estudiar",
               "estudiar", "tarea", "contenido", "titulo", "plan", "descripcion", "examen", "subject"),
    "lugar": ("lugar", "aula", "sala", "donde", "sitio", "room"),
    "tipo": ("tipo", "type", "categoria"),
}

# Lo que se descarga con "Descargar plantilla"
PLANTILLA = ("fecha;desde;hasta;qué;lugar\n"
             "2026-12-01;09:00;11:00;Estudiar Marketing Estratégico;Biblioteca\n"
             "2026-12-01;16:00;18:00;Repasar Derecho de la Comunicación;Casa\n"
             "2026-12-02;10:00;12:30;Ejercicios de Estadística;\n")


def columna_de(titulo):
    """Qué columna es un título ("Hora de inicio" -> "desde"), o None."""
    t = " ".join(re.sub(r"[^a-z ]", " ", sin_tildes(titulo)).split())
    if not t or len(t) > 30:
        return None
    for columna, nombres in TITULOS.items():
        if t in nombres:
            return columna
    return None


def fecha_de(valor, hoy=None):
    """Una fecha de la tabla -> "AAAA-MM-DD" (o None). Además de lo que entiende leer_fecha,
    acepta fechas sin año ("Lunes 1/12", "3 de diciembre"): se toma el año de las próximas semanas."""
    if isinstance(valor, (datetime, date)) or (isinstance(valor, str) and re.search(r"\d{4}", valor)):
        return leer_fecha(valor)
    if not isinstance(valor, str):
        return None
    texto = sin_tildes(valor)
    numeros = re.search(r"\b(\d{1,2})[/.-](\d{1,2})\b", texto)
    palabras = re.search(r"\b(\d{1,2})\s*(?:de\s+)?([a-z]{3,})", texto)
    if numeros:
        dia, mes = int(numeros.group(1)), int(numeros.group(2))
    elif palabras:
        mes = next((n for m, n in MESES.items() if m.startswith(palabras.group(2)[:3])), None)
        if not mes:
            return None
        dia = int(palabras.group(1))
    else:
        return None
    hoy = hoy or date.today()
    for anio in (hoy.year, hoy.year + 1):
        try:
            fecha = date(anio, mes, dia)
        except ValueError:
            return None
        if (hoy - fecha).days <= 120:   # si ya pasó hace meses, es la del año que viene
            return fecha.isoformat()
    return None


def texto_de(valor):
    """Una casilla como texto limpio (sin saltos de línea dobles)."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\s+", " ", str(valor)).strip()


def cosa(nombre, fecha, inicio=None, fin=None, lugar="", tipo=""):
    return {"nombre": nombre[:120], "fecha": fecha, "dia": None, "hora_inicio": inicio or "",
            "hora_fin": fin or "", "lugar": (lugar or "")[:60], "tipo": (tipo or "").lower()[:30]}


def leer_lista(filas):
    """Forma 1: busca la fila de títulos (con fecha y qué) y lee una cosa por fila."""
    for numero, fila in enumerate(filas[:15]):
        orden = [columna_de(celda) if isinstance(celda, str) else None for celda in fila]
        if "fecha" not in orden or "nombre" not in orden:
            continue
        cosas, fecha_actual = [], None
        for otra in filas[numero + 1:]:
            datos = {}
            for columna, valor in zip(orden, otra):
                if columna and columna not in datos:
                    datos[columna] = valor
            nombre = texto_de(datos.get("nombre"))
            fecha = fecha_de(datos.get("fecha")) if texto_de(datos.get("fecha")) else None
            fecha_actual = fecha or fecha_actual   # fecha vacía = la de arriba
            if not nombre or not fecha_actual:
                continue
            inicio, fin = leer_rango(datos.get("hora")) if texto_de(datos.get("hora")) else (None, None)
            if texto_de(datos.get("desde")):
                inicio = leer_rango(datos["desde"])[0]
            if texto_de(datos.get("hasta")):
                fin = leer_rango(datos["hasta"])[0]
            cosas.append(cosa(nombre, fecha_actual, inicio, fin, texto_de(datos.get("lugar")),
                              texto_de(datos.get("tipo"))))
        return cosas
    return None


def leer_cuadricula(filas):
    """Forma 2: una fila con varios días (las columnas) y debajo, por horas, qué haces cada día."""
    for numero, fila in enumerate(filas[:15]):
        dias = {i: fecha_de(celda) for i, celda in enumerate(fila) if texto_de(celda)}
        dias = {i: f for i, f in dias.items() if f}
        if len(dias) < 2:
            continue
        cosas = []
        for otra in filas[numero + 1:]:
            # La hora va en la primera casilla con algo, a la izquierda de los días
            primera = next((i for i, celda in enumerate(otra) if texto_de(celda)), None)
            if primera is None or primera >= min(dias):
                continue
            inicio, fin = leer_rango(otra[primera])
            for i, fecha in dias.items():
                nombre = texto_de(otra[i]) if i < len(otra) else ""
                if nombre:
                    cosas.append(cosa(nombre, fecha, inicio, fin))
        return cosas
    return None


def leer_sin_titulos(filas):
    """Sin fila de títulos: cada fila que tenga una fecha y un texto es una cosa."""
    cosas = []
    for fila in filas:
        celdas = [c for c in fila if texto_de(c)]
        fecha = next((f for f in (fecha_de(c) for c in celdas) if f), None)
        if not fecha:
            continue
        inicio = fin = None
        textos = []
        for celda in celdas:
            if fecha_de(celda):
                continue
            desde, hasta = leer_rango(celda)
            if desde and not inicio:
                inicio, fin = desde, hasta
            elif desde and not fin:
                fin = desde
            elif not desde:
                textos.append(texto_de(celda))
        if textos:
            cosas.append(cosa(max(textos, key=len), fecha, inicio, fin))
    return cosas


def leer_plan(nombre_archivo, contenido):
    """Lee el CSV o Excel y devuelve (cosas, problemas)."""
    cosas = []
    for _, filas in hojas_del_archivo(nombre_archivo, contenido):
        filas = [list(f) for f in filas if any(texto_de(c) for c in f)]
        leidas = leer_lista(filas)
        if leidas is None:
            leidas = leer_cuadricula(filas)
        if leidas is None:
            leidas = leer_sin_titulos(filas)
        cosas += leidas
    # Si la hora de fin es antes que la de inicio (o igual), la quitamos (ocupará una hora)
    for c in cosas:
        if c["hora_fin"] and c["hora_inicio"] and c["hora_fin"] <= c["hora_inicio"]:
            c["hora_fin"] = ""
    problemas = [] if cosas else ["No encontré filas con una fecha y qué hacer. Mira la plantilla de ejemplo."]
    return cosas, problemas
