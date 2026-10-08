# ============================================================
#  importar_horario.py - Leer el documento de "Sube tu horario"
#
#  Vale de dos formas (CSV o Excel):
#  1) Una fila por clase:
#         día | desde | hasta | materia | aula | tipo
#         Lunes | 09:00 | 11:00 | Cálculo | 2.14 | clase
#     (también "horario" con "9:00 - 11:00" en una sola columna; tipo vacío = clase)
#  2) La tabla de horario de siempre: los días arriba (Lunes, Martes...), las horas
#     a la izquierda ("08:00", "8:00 - 9:00") y en cada casilla la materia.
#     Si una materia ocupa varias horas seguidas, se junta en una sola clase.
#  Las materias del horario son las que luego salen en Tareas, Asistencia y "Mis materias".
# ============================================================

import re

from importar_eventos import hojas_del_archivo, leer_hora, sin_tildes

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIAS_CORTOS = {"lu": 0, "l": 0, "ma": 1, "m": 1, "mi": 2, "x": 2, "ju": 3, "j": 3, "vi": 4, "v": 4,
               "sa": 5, "s": 5, "do": 6, "d": 6, "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

# Lo que se descarga con "Descargar plantilla"
PLANTILLA = ("día;desde;hasta;materia;aula;tipo\n"
             "Lunes;09:00;11:00;Cálculo;2.14;clase\n"
             "Martes;12:00;14:00;Comunicación Corporativa;Aula 5;clase\n"
             "Miércoles;18:00;19:30;Gimnasio;Polideportivo;actividad\n")


def leer_dia(valor):
    """ "Lunes", "LUNES", "lun", "L", "Monday" -> 0 ... 6;  None si no es un día."""
    texto = re.sub(r"[^a-z]", "", sin_tildes(valor))
    if not texto:
        return None
    for numero, dia in enumerate(DIAS):
        if texto == dia or (len(texto) >= 3 and dia.startswith(texto)):
            return numero
    for numero, dia in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        if texto == dia:
            return numero
    return DIAS_CORTOS.get(texto)


def una_hora(valor):
    """ "09:00", "9.30", "11h" o solo "9" -> "09:00";  None si no es una hora."""
    if isinstance(valor, str) and re.fullmatch(r"\s*\d{1,2}\s*", valor) and int(valor) < 24:
        return f"{int(valor):02d}:00"
    return leer_hora(valor) or None


def leer_rango(valor):
    """ "9:00 - 11:00", "9 a 11h", "09.00-10.50" -> ("09:00", "11:00"); solo una hora -> ("09:00", None)."""
    if not isinstance(valor, str):
        return una_hora(valor), None   # celda de hora de Excel
    partes = re.split(r"\s*(?:-|–|—|\ba\b|hasta)\s*(?=\d)", valor.strip(), maxsplit=1)
    return una_hora(partes[0]), (una_hora(partes[1]) if len(partes) > 1 else None)


def a_minutos(hora):
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def de_minutos(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


COLUMNAS = {
    "dia": ("dia", "dias", "day", "jornada"),
    "desde": ("desde", "inicio", "hora inicio", "hora de inicio", "empieza", "comienza", "start"),
    "hasta": ("hasta", "fin", "hora fin", "hora de fin", "termina", "end"),
    "horario": ("horario", "hora", "horas", "franja", "time"),
    "nombre": ("materia", "asignatura", "nombre", "clase", "actividad", "curso", "subject"),
    "sala": ("aula", "sala", "lugar", "salon", "room", "edificio"),
    "tipo": ("tipo", "type"),
}


def columna_de(titulo):
    t = " ".join(re.sub(r"[^a-z ]", " ", sin_tildes(titulo)).split())
    for columna, nombres in COLUMNAS.items():
        if t in nombres:
            return columna
    return None


def leer_horario(nombre_archivo, contenido):
    """Lee el documento y devuelve (clases, problemas).
    clases = [{"nombre", "dia" (0-6), "hora_inicio", "hora_fin", "sala", "tipo" (None o "actividad")}]."""
    clases, problemas = [], []
    for nombre_hoja, filas in hojas_del_archivo(nombre_archivo, contenido):
        filas = [list(f) for f in filas]
        if not leer_lista(nombre_hoja, filas, clases, problemas):
            leer_tabla(filas, clases)
    # La misma clase repetida (por ejemplo en dos hojas) va una sola vez
    vistas, unicas = set(), []
    for clase in clases:
        clave = (clase["nombre"].lower(), clase["dia"], clase["hora_inicio"])
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(clase)
    if not unicas and not problemas:
        problemas.append("No encontré clases en el documento.")
    return unicas, problemas


def leer_lista(nombre_hoja, filas, clases, problemas):
    """Forma 1: una fila por clase. Devuelve False si la hoja no tiene esa forma."""
    orden = None
    for numero, fila in enumerate(filas, start=1):
        if not any(str(c or "").strip() for c in fila):
            continue
        if orden is None:
            titulos = [columna_de(c) if isinstance(c, str) else None for c in fila]
            if "dia" in titulos and "nombre" in titulos and ({"desde", "horario"} & set(titulos)):
                orden = titulos
            continue
        datos = {columna: fila[i] for i, columna in enumerate(orden) if columna and i < len(fila)}
        donde = f"Hoja {nombre_hoja}, fila {numero}" if nombre_hoja else f"Fila {numero}"
        nombre = " ".join(str(datos.get("nombre") or "").split())
        dia = leer_dia(datos.get("dia"))
        if "desde" in datos:
            inicio, fin = leer_rango(datos.get("desde"))
            fin = una_hora(datos.get("hasta")) if "hasta" in datos else fin
        else:
            inicio, fin = leer_rango(datos.get("horario"))
        if not nombre and dia is None:
            continue
        if not nombre or dia is None or not inicio or not fin or a_minutos(fin) <= a_minutos(inicio):
            problemas.append(f"{donde}: falta la materia, el día o las horas (o no se entienden).")
            continue
        tipo = "actividad" if "actividad" in sin_tildes(datos.get("tipo")) else None
        clases.append({"nombre": nombre[:80], "dia": dia, "hora_inicio": inicio, "hora_fin": fin,
                       "sala": " ".join(str(datos.get("sala") or "").split())[:60], "tipo": tipo})
    return orden is not None


def leer_tabla(filas, clases):
    """Forma 2: tabla con los días arriba y las horas a la izquierda."""
    # La fila de los días: la primera con al menos 3 días de la semana
    for fila_dias, fila in enumerate(filas):
        dias = {i: leer_dia(c) for i, c in enumerate(fila) if isinstance(c, str) and len(c.strip()) > 1}
        dias = {i: d for i, d in dias.items() if d is not None}
        if len(set(dias.values())) >= 3:
            break
    else:
        return
    # Las horas: en la primera columna que tenga horas debajo de los días
    franjas = []   # [(número de fila, inicio, fin o None)]
    columna_horas = None
    for numero in range(fila_dias + 1, len(filas)):
        fila = filas[numero]
        for i, celda in enumerate(fila):
            if i in dias or celda is None or str(celda).strip() == "":
                continue
            if columna_horas not in (None, i):
                continue
            inicio, fin = leer_rango(celda)
            if inicio:
                columna_horas = i
                franjas.append((numero, inicio, fin))
            break
    if not franjas:
        return
    # Si una franja no dice cuándo termina, termina cuando empieza la siguiente (o dura 1 hora)
    completas = []
    for k, (numero, inicio, fin) in enumerate(franjas):
        if not fin:
            fin = franjas[k + 1][1] if k + 1 < len(franjas) else de_minutos(a_minutos(inicio) + 60)
        if a_minutos(fin) > a_minutos(inicio):
            completas.append((numero, inicio, fin))
    # Cada columna de día: las casillas iguales seguidas se juntan en una clase
    for i, dia in dias.items():
        abierta = None
        for numero, inicio, fin in completas + [(None, None, None)]:
            celda = filas[numero][i] if numero is not None and i < len(filas[numero]) else None
            texto = "\n".join(l.strip() for l in str(celda or "").splitlines() if l.strip())
            if abierta and texto == abierta["texto"] and inicio == abierta["hora_fin"]:
                abierta["hora_fin"] = fin   # sigue la misma materia
                continue
            if abierta:
                clases.append(clase_de_casilla(abierta["texto"], dia, abierta["hora_inicio"], abierta["hora_fin"]))
                abierta = None
            if texto:
                abierta = {"texto": texto, "hora_inicio": inicio, "hora_fin": fin}


def clase_de_casilla(texto, dia, inicio, fin):
    """ "Cálculo\\nAula 2.14" -> materia "Cálculo" y aula "Aula 2.14" (la primera línea es la materia)."""
    lineas = texto.split("\n")
    sala = next((l for l in lineas[1:] if re.search(r"\b(aula|sala|edif|lab|seminario)", sin_tildes(l))
                 or re.search(r"\d", l)), "")
    sala = re.sub(r"^aula\s*:?\s*", "", sala, flags=re.IGNORECASE)   # el horario ya pone "Aula" delante
    return {"nombre": lineas[0][:80], "dia": dia, "hora_inicio": inicio, "hora_fin": fin, "sala": sala[:60],
            "tipo": None}
