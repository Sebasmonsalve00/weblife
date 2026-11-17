# ============================================================
#  leer_imagen.py - Leer una foto o captura (PNG, JPG...) y sacar
#  las clases, entrenos y eventos que salen en ella.
#
#  Dos formas de leerla:
#  1) Con Claude (la IA de Anthropic), si en el archivo WSGI de PythonAnywhere
#     está la clave WEBLIFE_CLAUDE_CLAVE. Entiende casi cualquier imagen:
#     horarios semanales, calendarios de exámenes, carteles, planes de entreno...
#     PythonAnywhere gratis sí deja hablar con api.anthropic.com.
#  2) Sin clave: la foto se lee en el navegador con Tesseract (static/leer_foto.js)
#     y aquí solo llega el texto. Con eventos_de_texto() buscamos en cada línea
#     una fecha ("12/12/2026", "12 de diciembre") y una hora.
#
#  Lo que sale es una lista de cosas, cada una con:
#      nombre, fecha ("2026-12-02" o ""), dia (0 = lunes ... 6 = domingo, o None),
#      hora_inicio ("09:00" o ""), hora_fin, lugar, tipo
#  Si tiene fecha va al Calendario (y sale en el Horario ese día).
#  Si solo dice el día de la semana, es algo que se repite: va al Horario.
# ============================================================

import base64
import json
import os
import re
from datetime import date

from importar_eventos import MESES, leer_fecha, leer_hora, sin_tildes

CLAVE = (os.environ.get("WEBLIFE_CLAUDE_CLAVE") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
MODELO = "claude-opus-5-5"
TIPOS_IMAGEN = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
                "webp": "image/webp"}
MAXIMO = 5 * 1024 * 1024   # Claude acepta imágenes de hasta 5 MB
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def es_imagen(nombre_archivo, tipo=""):
    """True si el archivo subido es una foto (por su nombre o por su tipo)."""
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    return extension in TIPOS_IMAGEN or (tipo or "").startswith("image/")


def tipo_de(nombre_archivo, contenido):
    """El tipo de la imagen mirando sus primeros bytes (más fiable que el nombre)."""
    if contenido.startswith(b"\x89PNG"):
        return "image/png"
    if contenido.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if contenido[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
    if extension in TIPOS_IMAGEN:
        return TIPOS_IMAGEN[extension]
    raise ValueError("Ese formato de imagen no lo puedo leer. Usa PNG o JPG (una captura de pantalla vale).")


def disponible():
    """¿Podemos leer fotos con Claude? (hay clave y está instalada la librería "anthropic")."""
    if not CLAVE:
        return False
    try:
        import anthropic  # noqa: F401  (solo miramos si está instalada)
    except ImportError:
        return False
    return True


# ---------- Lo que le pedimos a Claude ----------

def _texto(descripcion):
    return {"type": "string", "description": descripcion}


ESQUEMA_COSAS = {
    "type": "object",
    "properties": {"cosas": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "nombre": _texto("Nombre de la clase, entreno, examen o evento"),
            "fecha": _texto("Fecha exacta AAAA-MM-DD si la imagen la da; si no, vacío"),
            "dia": _texto("Si se repite cada semana (horario semanal): lunes, martes, miercoles, jueves, "
                          "viernes, sabado o domingo. Si tiene fecha exacta, vacío"),
            "hora_inicio": _texto("HH:MM en 24 h, o vacío"),
            "hora_fin": _texto("HH:MM en 24 h, o vacío"),
            "lugar": _texto("Aula, sala o sitio, o vacío"),
            "tipo": _texto("clase, actividad, examen, entrega, entrenamiento, comida, cardio, fuerza... o vacío"),
        },
        "required": ["nombre", "fecha", "dia", "hora_inicio", "hora_fin", "lugar", "tipo"],
        "additionalProperties": False,
    }}},
    "required": ["cosas"],
    "additionalProperties": False,
}

ESQUEMA_EVENTOS = {
    "type": "object",
    "properties": {"eventos": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "fecha": _texto("AAAA-MM-DD"),
            "hora": _texto("HH:MM en 24 h (la de inicio), o vacío"),
            "nombre": _texto("Asignatura o nombre del evento"),
            "tipo": _texto("Examen, Entrega, Presentación, Festivo... (vacío = Examen)"),
            "carrera": _texto("Grado o carrera, tal como lo dice la imagen (por ejemplo en un título "
                              "encima de la tabla), o vacío"),
            "curso": _texto("Año de carrera (1, 2, 3, 4...), o vacío"),
        },
        "required": ["fecha", "hora", "nombre", "tipo", "carrera", "curso"],
        "additionalProperties": False,
    }}},
    "required": ["eventos"],
    "additionalProperties": False,
}


def _preguntar_a_claude(contenido, tipo, instrucciones, esquema):
    """Manda la imagen a Claude y devuelve su respuesta ya convertida en diccionario."""
    import anthropic

    if len(contenido) > MAXIMO:
        raise ValueError("La foto es demasiado grande (máximo 5 MB). Prueba con una captura de pantalla.")
    cliente = anthropic.Anthropic(api_key=CLAVE, timeout=120.0)
    hoy = date.today()
    try:
        # "fallbacks": si el modelo no quiere leer la imagen, la API prueba sola con otro modelo
        respuesta = cliente.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": esquema}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": tipo,
                                             "data": base64.standard_b64encode(contenido).decode("ascii")}},
                {"type": "text", "text": f"Hoy es {DIAS[hoy.weekday()]} {hoy.isoformat()}. " + instrucciones},
            ]}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("La clave de Claude (WEBLIFE_CLAUDE_CLAVE) no es válida. Revísala en el archivo WSGI.")
    except anthropic.PermissionDeniedError:
        raise ValueError("La clave de Claude no tiene permiso o no tiene saldo. Revisa tu cuenta en console.anthropic.com.")
    except anthropic.RateLimitError:
        raise ValueError("Claude está ocupado ahora mismo. Prueba otra vez en un minuto.")
    except anthropic.BadRequestError as error:
        mensaje = str(getattr(error, "message", "") or error)
        if "credit" in mensaje.lower() or "balance" in mensaje.lower():
            raise ValueError("Tu cuenta de Claude no tiene saldo. Añade crédito en console.anthropic.com.")
        raise ValueError("Claude no pudo leer esa imagen. Prueba con una captura más nítida.")
    except anthropic.APIConnectionError:
        raise ValueError("No pude conectar con Claude. Prueba otra vez en un rato.")
    except anthropic.APIStatusError:
        raise ValueError("Claude tuvo un problema leyendo la foto. Prueba otra vez en un rato.")

    if respuesta.stop_reason == "refusal":
        raise ValueError("Claude no quiso leer esa imagen. Prueba con otra captura.")
    texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
    try:
        return json.loads(texto)
    except ValueError:
        raise ValueError("No entendí lo que salió de la foto. Prueba otra vez.")


def leer_cosas(nombre_archivo, contenido, modo="universidad"):
    """Lee una foto de un horario, plan de entrenos o calendario y devuelve sus cosas
    (ver arriba). Cada cosa trae o fecha (va al Calendario) o día de la semana (va al Horario)."""
    tipo = tipo_de(nombre_archivo, contenido)
    que = ("entrenos, comidas y actividades deportivas" if modo == "deporte"
           else "clases, exámenes, entregas y eventos de la universidad")
    instrucciones = (
        f"Esta imagen es de un estudiante que quiere pasar a su agenda sus {que}. "
        "Saca cada cosa que aparezca con su nombre, horas y lugar. "
        "Si la imagen es un horario semanal que se repite (columnas Lunes, Martes...), pon 'dia' y deja 'fecha' vacía. "
        "Si la cosa tiene una fecha concreta (un calendario, una lista de exámenes, '12 de diciembre'...), "
        "pon 'fecha' en AAAA-MM-DD y deja 'dia' vacío. Si falta el año, usa el de la próxima vez que llegue esa fecha. "
        "Si un horario semanal muestra también las fechas de cada día (por ejemplo 'lun 5/10'), trátalo como semanal. "
        "No inventes nada que no salga en la imagen. Si no hay nada, devuelve la lista vacía.")
    datos = _preguntar_a_claude(contenido, tipo, instrucciones, ESQUEMA_COSAS)
    return limpiar_cosas(datos.get("cosas", []))


def leer_eventos(nombre_archivo, contenido, convocatoria=""):
    """Lee la foto de un calendario oficial de exámenes/eventos (para "Añade tus eventos").
    Devuelve el mismo documento como texto CSV, para leerlo con importar_eventos como si fuera un Excel."""
    tipo = tipo_de(nombre_archivo, contenido)
    instrucciones = (
        "Esta imagen es un calendario oficial de exámenes o eventos de una universidad"
        + (f" (convocatoria {convocatoria})" if convocatoria else "") + ". "
        "Saca una fila por cada examen o evento con su fecha, hora de inicio, nombre, tipo, carrera y año de carrera. "
        "La carrera y el año suelen salir como títulos encima de cada tabla ('1º Curso – Grado en Marketing'): "
        "repítelos en cada fila que quede debajo. Si falta el año de la fecha, usa el de la próxima vez que llegue. "
        "No inventes nada que no salga en la imagen.")
    datos = _preguntar_a_claude(contenido, tipo, instrucciones, ESQUEMA_EVENTOS)
    return eventos_a_csv(datos.get("eventos", []))


# ---------- Ordenar lo leído ----------

def _dia_semana(valor):
    texto = re.sub(r"[^a-z]", "", sin_tildes(valor))
    for numero, dia in enumerate(DIAS):
        if texto and (texto == dia or (len(texto) >= 3 and dia.startswith(texto))):
            return numero
    return None


def limpiar_cosas(cosas):
    """Deja solo las cosas que se entienden, con las fechas y horas en el formato de la web."""
    limpias = []
    for cosa in cosas:
        nombre = re.sub(r"\s+", " ", str(cosa.get("nombre", ""))).strip()[:120]
        if not nombre:
            continue
        fecha = leer_fecha(cosa.get("fecha", "")) if cosa.get("fecha") else None
        dia = None if fecha else _dia_semana(cosa.get("dia", ""))
        if fecha is None and dia is None:
            continue   # ni fecha ni día: no sabemos dónde ponerlo
        inicio = leer_hora(cosa.get("hora_inicio", "")) or ""
        fin = leer_hora(cosa.get("hora_fin", "")) or ""
        limpias.append({"nombre": nombre, "fecha": fecha, "dia": dia, "hora_inicio": inicio, "hora_fin": fin,
                        "lugar": str(cosa.get("lugar", "")).strip()[:60],
                        "tipo": str(cosa.get("tipo", "")).strip().lower()[:30]})
    return limpias


def eventos_a_csv(eventos):
    """Convierte la lista de eventos en el CSV de la plantilla (fecha;hora;nombre;tipo;carrera;año).
    Si la foto no dice la carrera o el año, se guardan como "General" / "Todos los cursos"."""
    def celda(valor):
        return str(valor or "").replace(";", ",").replace("\n", " ").strip()
    lineas = ["fecha;hora;nombre;tipo;carrera;año"]
    for e in eventos:
        e = dict(e, carrera=e.get("carrera") or "General", curso=e.get("curso") or "Todos los cursos")
        lineas.append(";".join(celda(e.get(c)) for c in ("fecha", "hora", "nombre", "tipo", "carrera", "curso")))
    return "\n".join(lineas) + "\n"


# ---------- Sin Claude: el texto que leyó Tesseract en el navegador ----------

PATRON_FECHA = re.compile(
    r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b"                       # 12/12/2026, 2-12, 2.12.26
    r"|\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(MESES) + r")(?:\s+(?:de\s+)?(\d{4}))?",   # 12 de diciembre (de 2026)
    re.IGNORECASE)
PATRON_HORA = re.compile(r"\b([01]?\d|2[0-3])[:.h]([0-5]\d)\b|\b([01]?\d|2[0-3])\s*h\b", re.IGNORECASE)


def _fecha_de(coincidencia):
    """La fecha de una coincidencia de PATRON_FECHA, en AAAA-MM-DD (o None)."""
    hoy = date.today()
    try:
        if coincidencia.group(1):
            dia, mes, anio = int(coincidencia.group(1)), int(coincidencia.group(2)), coincidencia.group(3)
        else:
            dia, mes = int(coincidencia.group(4)), MESES[sin_tildes(coincidencia.group(5))]
            anio = coincidencia.group(6)
        if anio:
            anio = int(anio) + (2000 if len(anio) == 2 else 0)
            return date(anio, mes, dia).isoformat()
        fecha = date(hoy.year, mes, dia)
        if fecha < hoy.replace(day=1):   # sin año: la próxima vez que llegue
            fecha = date(hoy.year + 1, mes, dia)
        return fecha.isoformat()
    except (ValueError, KeyError):
        return None


def eventos_de_texto(texto):
    """Busca en cada línea del texto una fecha (y si hay, una hora). Lo que queda es el nombre.
    Si una línea tiene fecha pero no nombre, el nombre puede venir en la línea de al lado."""
    cosas = []
    lineas = [re.sub(r"\s+", " ", l).strip() for l in str(texto or "").splitlines()]
    lineas = [l for l in lineas if l]
    for i, linea in enumerate(lineas):
        fecha_hallada = PATRON_FECHA.search(linea)
        if not fecha_hallada:
            continue
        fecha = _fecha_de(fecha_hallada)
        if not fecha:
            continue
        resto = linea[:fecha_hallada.start()] + " " + linea[fecha_hallada.end():]
        horas = []
        for h in PATRON_HORA.finditer(resto):
            horas.append(f"{int(h.group(1) or h.group(3)):02d}:{h.group(2) or '00'}")
        resto = PATRON_HORA.sub(" ", resto)
        # Fuera palabras de días ("lunes", "lun.") y signos sueltos
        resto = re.sub(r"\b(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo|lun|mar|mi[eé]|jue|vie|"
                       r"s[aá]b|dom)\b\.?,?", " ", resto, flags=re.IGNORECASE)
        nombre = re.sub(r"^[\s\-–—|:,.;]+|[\s\-–—|:,.;]+$", "", re.sub(r"\s+", " ", resto)).strip()
        if len(re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúÑñ]", "", nombre)) < 3:
            # sin nombre en esta línea: probamos la de antes (si no tiene fecha)
            anterior = lineas[i - 1] if i > 0 else ""
            nombre = anterior if anterior and not PATRON_FECHA.search(anterior) else ""
        if not nombre:
            continue
        cosas.append({"nombre": nombre[:120], "fecha": fecha, "dia": None,
                      "hora_inicio": horas[0] if horas else "", "hora_fin": horas[1] if len(horas) > 1 else "",
                      "lugar": "", "tipo": ""})
    return cosas
