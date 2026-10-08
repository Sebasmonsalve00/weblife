# ============================================================
#  importar_eventos.py - Leer el documento de "Añade tus eventos"
#
#  El documento es una tabla (CSV o Excel) con una fila por evento:
#      fecha | hora | nombre | tipo | carrera | año
#      2026-12-02 | 16:00 | Corporate Communication | Examen | Grado en Marketing | 2
#  Un mismo documento puede traer varias carreras y varios años: se guardan todos.
#  - fecha: "2026-12-02", "02/12/2026" o "02-12-2026" (o una celda de fecha en Excel)
#  - hora: "16:00" o vacía si no tiene hora
#  - tipo: qué es (Examen, Entrega, Presentación, Festivo...). Vacío = Examen.
#  - carrera: "Grado en Marketing"...   - año: "2", "2º" o "2º Curso" (se guarda como "2º Curso")
#  La primera fila puede tener los títulos de las columnas (en cualquier orden).
# ============================================================

import csv
import io
import re
from datetime import date, datetime, time

COLUMNAS = ("fecha", "hora", "nombre", "tipo", "carrera", "curso")

# Otras formas de llamar a cada columna en la primera fila
SINONIMOS = {
    "fecha": "fecha", "dia": "fecha", "día": "fecha", "date": "fecha",
    "hora": "hora", "time": "hora",
    "nombre": "nombre", "evento": "nombre", "asignatura": "nombre", "materia": "nombre", "name": "nombre",
    "tipo": "tipo", "naturaleza": "tipo", "clase": "tipo", "type": "tipo",
    "carrera": "carrera", "grado": "carrera", "titulación": "carrera", "titulacion": "carrera",
    "estudios": "carrera", "degree": "carrera",
    "año": "curso", "ano": "curso", "curso": "curso", "year": "curso", "año de carrera": "curso",
}

# Lo que se descarga con "Descargar plantilla"
PLANTILLA = ("fecha;hora;nombre;tipo;carrera;año\n"
             "2026-12-02;16:00;Corporate Communication;Examen;Grado en Marketing;2\n"
             "2026-12-07;12:00;Brand Management;Examen;Grado en Marketing;3\n"
             "2026-12-10;;Trabajo final de Branding;Entrega;Grado en Periodismo;2\n")


def leer_fecha(valor):
    """Convierte la fecha de la tabla en "AAAA-MM-DD" (o None si no se entiende)."""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            pass
    return None


def leer_hora(valor):
    """Convierte la hora en "HH:MM", o None si está vacía. Devuelve False si no se entiende."""
    if isinstance(valor, (datetime, time)):
        return valor.strftime("%H:%M")
    texto = str(valor or "").strip().lower().replace("h", "").replace(".", ":")
    if not texto:
        return None
    for formato in ("%H:%M", "%H:%M:%S", "%H"):
        try:
            return datetime.strptime(texto, formato).strftime("%H:%M")
        except ValueError:
            pass
    return False


def leer_curso(valor):
    """Convierte el año en "2º Curso" (acepta 2, "2", "2º", "2º Curso", "Segundo"...)."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor or "").strip()
    numero = re.fullmatch(r"(\d)\s*(º|°|o|er|ro|do|to)?\.?\s*(curso|año)?", texto, re.IGNORECASE)
    if numero:
        return f"{numero.group(1)}º Curso"
    palabras = {"primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5, "sexto": 6}
    primera = texto.lower().split(" ")[0] if texto else ""
    return f"{palabras[primera]}º Curso" if primera in palabras else texto


def filas_del_archivo(nombre_archivo, contenido):
    """Saca las filas (listas de celdas) de un CSV o de un Excel (.xlsx)."""
    if nombre_archivo.lower().endswith(".xlsx"):
        try:
            import openpyxl   # viene instalado en PythonAnywhere
        except ImportError:
            raise ValueError("Este servidor no puede leer Excel: guarda la tabla como CSV y súbela otra vez.")
        libro = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        return [list(fila) for fila in libro.active.iter_rows(values_only=True)]
    if nombre_archivo.lower().endswith((".csv", ".txt")):
        texto = contenido.decode("utf-8-sig", errors="replace")
        # Excel en español guarda los CSV con ";" en vez de ","
        separador = ";" if texto.count(";") >= texto.count(",") else ","
        return list(csv.reader(io.StringIO(texto), delimiter=separador))
    raise ValueError("El documento tiene que ser una tabla CSV o Excel (.xlsx).")


def leer_eventos(nombre_archivo, contenido):
    """Lee el documento y devuelve (eventos, problemas).
    eventos = [{"fecha", "hora", "nombre", "tipo", "carrera", "curso"}, ...]; problemas = textos con las filas que no se entendieron."""
    filas = [fila for fila in filas_del_archivo(nombre_archivo, contenido)
             if any(str(celda or "").strip() for celda in fila)]
    if not filas:
        return [], ["El documento está vacío."]

    # ¿La primera fila son los títulos? Si sí, usamos su orden; si no, fecha | hora | nombre | tipo.
    titulos = [SINONIMOS.get(str(celda or "").strip().lower()) for celda in filas[0]]
    if "fecha" in titulos and "nombre" in titulos:
        orden = titulos
        filas = filas[1:]
        primera = 2
    else:
        orden = list(COLUMNAS)
        primera = 1

    eventos, problemas = [], []
    for numero, fila in enumerate(filas, start=primera):
        datos = {columna: fila[i] for i, columna in enumerate(orden) if columna and i < len(fila)}
        fecha = leer_fecha(datos.get("fecha"))
        hora = leer_hora(datos.get("hora"))
        nombre = str(datos.get("nombre") or "").strip()
        tipo = str(datos.get("tipo") or "").strip().capitalize() or "Examen"
        carrera = str(datos.get("carrera") or "").strip()
        curso = leer_curso(datos.get("curso"))
        if not fecha or not nombre or hora is False:
            problemas.append(f"Fila {numero}: falta la fecha o el nombre, o no se entiende la hora.")
            continue
        if not carrera or not curso:
            problemas.append(f"Fila {numero}: falta la carrera o el año.")
            continue
        eventos.append({"fecha": fecha, "hora": hora, "nombre": nombre[:120], "tipo": tipo[:40],
                        "carrera": carrera[:80], "curso": curso[:40]})
    return eventos, problemas


def es_examen(tipo):
    """Los eventos de tipo examen van a "Próximos exámenes"; el resto, como eventos normales."""
    return "examen" in (tipo or "examen").lower()
