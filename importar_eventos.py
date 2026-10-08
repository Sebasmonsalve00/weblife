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
#  Los títulos de las columnas pueden estar en cualquier orden y no hace falta que sean
#  la primera fila (los calendarios oficiales suelen traer un título encima).
#  También vale un Excel con una hoja por carrera o por curso, o con filas de título
#  como "GRADO EN PERIODISMO" o "2º CURSO" encima de sus exámenes.
# ============================================================

import csv
import io
import re
import unicodedata
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


MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def sin_tildes(texto):
    """ "Titulación" -> "titulacion" (para comparar títulos de columnas)."""
    texto = unicodedata.normalize("NFD", str(texto or "").strip().lower())
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")


def columna_de(titulo):
    """Qué columna es un título: "Fecha del examen" -> "fecha", "Titulación" -> "carrera"..."""
    t = sin_tildes(titulo)
    if not t:
        return None
    if t in SINONIMOS:
        return SINONIMOS[t]
    for palabras, columna in ((("fecha", "dia", "date"), "fecha"), (("hora", "horario", "time", "inicio"), "hora"),
                              (("titulacion", "grado", "carrera", "estudios", "degree"), "carrera"),
                              (("curso", "ano", "year"), "curso"),
                              (("asignatura", "materia", "nombre", "evento", "examen", "prueba"), "nombre"),
                              (("tipo", "naturaleza"), "tipo")):
        if any(re.search(rf"\b{p}\b", t) for p in palabras):
            return columna
    return None


def leer_fecha(valor):
    """Convierte la fecha de la tabla en "AAAA-MM-DD" (o None si no se entiende).
    Entiende "2026-12-02", "02/12/2026", "2-12-26" y "miércoles, 2 de diciembre de 2026"."""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = sin_tildes(valor)
    numeros = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", texto)
    if numeros:
        anio, mes, dia = (int(x) for x in numeros.groups())
    else:
        numeros = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", texto)
        if numeros:
            dia, mes, anio = (int(x) for x in numeros.groups())
        else:
            palabras = re.search(r"(\d{1,2})\s*(?:de\s+)?([a-z]+)\.?\s*(?:de\s+|del\s+)?(\d{4})", texto)
            mes_texto = palabras and next((n for m, n in MESES.items() if m.startswith(palabras.group(2)[:3])), None)
            if not mes_texto:
                return None
            dia, mes, anio = int(palabras.group(1)), mes_texto, int(palabras.group(3))
    if anio < 100:
        anio += 2000
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        return None


def leer_hora(valor):
    """Convierte la hora en "HH:MM", o None si está vacía. Devuelve False si no se entiende."""
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M") if (valor.hour or valor.minute) else None
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    texto = str(valor or "").strip().lower()
    if not texto or texto.strip("-–— ") == "" or texto in ("sin hora", "por determinar", "pd"):
        return None
    # "16:00", "16.00 h", "9:30 - 11:30" (nos quedamos con la primera), "16h"
    encontrada = re.search(r"(\d{1,2})\s*[:.h]\s*(\d{2})", texto) or re.search(r"\b(\d{1,2})\s*h\b", texto)
    if not encontrada:
        return False
    hora = int(encontrada.group(1))
    minutos = int(encontrada.group(2)) if encontrada.lastindex > 1 else 0
    return f"{hora:02d}:{minutos:02d}" if hora < 24 and minutos < 60 else False


def leer_curso(valor):
    """Convierte el año en "2º Curso" (acepta 2, "2", "2º", "2º Curso", "Segundo"...)."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor or "").strip()
    numero = (re.fullmatch(r"(\d)\s*(º|°|ª|o|er|ro|do|to)?\.?\s*(curso|año)?", texto, re.IGNORECASE)
              or re.search(r"(\d)\s*(?:º|°|ª|o|er|ro|do|to)?\.?\s*curso", texto, re.IGNORECASE)
              or re.search(r"curso\s*(\d)", texto, re.IGNORECASE))
    if numero:
        return f"{numero.group(1)}º Curso"
    palabras = {"primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5, "sexto": 6}
    primera = texto.lower().split(" ")[0] if texto else ""
    return f"{palabras[primera]}º Curso" if primera in palabras else texto


def hojas_del_archivo(nombre_archivo, contenido):
    """Saca las hojas de un CSV o de un Excel: [(nombre de la hoja, filas)]. Un CSV es una sola hoja."""
    if nombre_archivo.lower().endswith(".xlsx"):
        try:
            import openpyxl   # viene instalado en PythonAnywhere
        except ImportError:
            raise ValueError("Este servidor no puede leer Excel: guarda la tabla como CSV y súbela otra vez.")
        libro = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        return [(hoja.title, [list(fila) for fila in hoja.iter_rows(values_only=True)]) for hoja in libro.worksheets]
    if nombre_archivo.lower().endswith((".csv", ".txt")):
        texto = contenido.decode("utf-8-sig", errors="replace")
        # Excel en español guarda los CSV con ";" en vez de ","
        separador = ";" if texto.count(";") >= texto.count(",") else ","
        return [("", list(csv.reader(io.StringIO(texto), delimiter=separador)))]
    raise ValueError("El documento tiene que ser una tabla CSV o Excel (.xlsx).")


def es_carrera(texto):
    """¿Esta celda suelta es el nombre de una carrera? ("GRADO EN PERIODISMO", "Doble grado en...")"""
    return bool(re.match(r"(doble\s+)?(grado|titulacion|licenciatura|master|degree|bachelor)\b", sin_tildes(texto)))


def es_curso(texto):
    """¿Esta celda suelta es un curso? ("2º CURSO", "Curso 3", "Primer curso")"""
    t = sin_tildes(texto)
    return len(t) < 25 and bool(re.search(r"\d\s*(o|º|°|ª|er|ro|do|to)?\.?\s*curso|curso\s*\d|"
                                          r"^(primer|primero|segundo|tercer|tercero|cuarto|quinto|sexto)\s+curso", t))


def nombre_carrera(texto):
    """Pone las carreras igual aunque el documento las escriba distinto:
    "Grado Periodismo", "Grado de Marketing" y "Marketing" -> "Grado en Periodismo", "Grado en Marketing"."""
    texto = " ".join(str(texto).split())
    if re.match(r"(doble\s+grado|master|máster|titulaci)", texto, re.IGNORECASE):
        return texto
    resto = re.sub(r"^grado\s*(en|de)?\s+", "", texto, flags=re.IGNORECASE).strip()
    return f"Grado en {resto[:1].upper()}{resto[1:]}" if resto else texto


def leer_seccion(texto):
    """Una fila de título de un bloque del documento -> (carrera, curso), o (None, None) si no lo es.
    "1º Curso – Grado Comunicación Audiovisual" -> ("Grado en Comunicación Audiovisual", "1º Curso")
    "GRADO EN PERIODISMO" -> ("Grado en Periodismo", None);  "2º CURSO" -> (None, "2º Curso")
    "ASIGNATURAS OPTATIVAS" -> ("Optativas", "Todos los cursos")"""
    texto = " ".join(str(texto).split())
    if re.match(r"asignaturas?\s+\S", sin_tildes(texto)):
        resto = re.sub(r"^asignaturas?\s+", "", texto, flags=re.IGNORECASE)
        return resto[:1].upper() + resto[1:].lower(), "Todos los cursos"
    partes = [p for p in re.split(r"\s*[–—-]\s*", texto, maxsplit=1) if p]
    if len(partes) == 2:
        if es_curso(partes[0]):
            return nombre_carrera(partes[1]), leer_curso(partes[0])
        if es_curso(partes[1]):
            return nombre_carrera(partes[0]), leer_curso(partes[1])
    if es_curso(texto):
        return None, leer_curso(texto)
    if es_carrera(texto):
        return nombre_carrera(texto.title() if texto.isupper() else texto), None
    return None, None


def leer_eventos(nombre_archivo, contenido):
    """Lee el documento y devuelve (eventos, problemas).
    eventos = [{"fecha", "hora", "nombre", "tipo", "carrera", "curso"}, ...]; problemas = textos con las filas que no se entendieron."""
    eventos, problemas = [], []
    for nombre_hoja, filas in hojas_del_archivo(nombre_archivo, contenido):
        leer_hoja(nombre_hoja, filas, eventos, problemas)
    if not eventos and not problemas:
        problemas.append("El documento está vacío.")
    return eventos, problemas


def leer_hoja(nombre_hoja, filas, eventos, problemas):
    """Lee una hoja: busca la fila de títulos, y luego cada fila es un evento.
    La carrera y el curso salen de su columna; si no hay, de una fila de título encima
    ("GRADO EN PERIODISMO", "2º CURSO") o del nombre de la hoja."""
    # Carrera y curso que dice el nombre de la hoja (si dice algo)
    carrera_actual = nombre_hoja.strip() if es_carrera(nombre_hoja) else ""
    curso_actual = leer_curso(nombre_hoja) if es_curso(nombre_hoja) else ""

    orden = None
    for numero, fila in enumerate(filas, start=1):
        celdas = [c for c in fila if str(c or "").strip()]
        if not celdas:
            continue
        # ¿Es la fila de títulos? (tiene al menos "fecha" y "nombre")
        titulos = [columna_de(c) if isinstance(c, str) else None for c in fila]
        if "fecha" in titulos and "nombre" in titulos:
            orden = titulos
            continue
        # Filas de título de un bloque: "1º Curso – Grado en Periodismo", "GRADO EN PERIODISMO", "2º CURSO"...
        # (también las que no tienen fecha, como "Antropología | detalle en enlace": se saltan)
        if len(celdas) <= 2 and all(isinstance(c, str) for c in celdas) and not any(leer_fecha(c) for c in celdas):
            for c in celdas:
                carrera, curso = leer_seccion(c)
                carrera_actual = carrera or carrera_actual
                curso_actual = curso or curso_actual
            continue
        if orden is None:
            if leer_fecha(fila[0] if fila else None) and len(fila) >= 3:
                orden = list(COLUMNAS)   # sin títulos: fecha | hora | nombre | tipo | carrera | año
            else:
                continue                 # texto de encabezado del documento: lo saltamos

        datos = {columna: fila[i] for i, columna in enumerate(orden) if columna and i < len(fila)}
        fecha = leer_fecha(datos.get("fecha"))
        hora = leer_hora(datos.get("hora"))
        if hora is None and isinstance(datos.get("fecha"), datetime):
            hora = leer_hora(datos["fecha"])   # fecha y hora en la misma celda
        nombre = str(datos.get("nombre") or "").strip()
        tipo = str(datos.get("tipo") or "").strip().capitalize() or "Examen"
        carrera = str(datos.get("carrera") or "").strip() or carrera_actual
        curso = leer_curso(datos.get("curso")) or curso_actual
        donde = f"Hoja {nombre_hoja}, fila {numero}" if nombre_hoja else f"Fila {numero}"
        if not fecha and not nombre:
            continue   # fila de notas o vacía
        if not fecha or not nombre or hora is False:
            problemas.append(f"{donde}: falta la fecha o el nombre, o no se entiende la hora.")
            continue
        if not carrera or not curso:
            problemas.append(f"{donde}: falta la carrera o el año.")
            continue
        eventos.append({"fecha": fecha, "hora": hora, "nombre": nombre[:120], "tipo": tipo[:40],
                        "carrera": carrera[:80], "curso": curso[:40]})


def es_examen(tipo):
    """Los eventos de tipo examen van a "Próximos exámenes"; el resto, como eventos normales."""
    return "examen" in (tipo or "examen").lower()
