# ============================================================
#  contenido.py - Los textos de la web
#
#  Aquí están los títulos, subtítulos, el menú, el footer y los
#  mensajes. Si quieres cambiar cómo se llama algo, cámbialo aquí
#  y no en el HTML. app.py se los pasa a todas las plantillas.
# ============================================================

NOMBRE_SITIO = "weblife"

# ---- Menú de navegación ----
# Cada enlace: (texto que se ve, nombre de la ruta en app.py)
MENU = [
    ("Horario", "horario"),
    ("Tareas", "tareas"),
    ("Pendientes", "pendientes"),
    ("Calendario", "calendario_vista"),
    ("Asistencia", "asistencia"),
]

# En Deporte, el menú cambia el nombre de la primera página
MENU_DEPORTE = [
    ("Entrenos", "horario"),
    ("Metas", "tareas"),
    ("Pendientes", "pendientes"),
    ("Calendario", "calendario_vista"),
    ("Alimentación e info", "asistencia"),
]


def menu(modo="universidad"):
    """El menú del calendario que estás usando."""
    return MENU_DEPORTE if modo == "deporte" else MENU


# Botón en píldora a la derecha del menú
BOTON_MENU = {"texto": "Mi perfil", "ruta": "perfil"}
TEXTO_SALIR = "Salir"

# ---- Encabezado de cada página ----
# etiqueta = texto pequeño arriba del título, subtitulo = texto gris debajo
PAGINAS = {
    "horario": {
        "etiqueta": "Universidad",
        "titulo": "Horario semanal",
        "subtitulo": "Tus clases de 8:00 a 20:00, tu asistencia y las tareas que te dejan.",
    },
    "tareas": {
        "etiqueta": "Universidad",
        "titulo": "Tareas",
        "subtitulo": "Todo lo que tienes que entregar, con su materia y sus fechas.",
    },
    "pendientes": {
        "etiqueta": "Universidad",
        "titulo": "Pendientes",
        "subtitulo": "Lo que falta por hacer, ordenado por fecha de entrega.",
    },
    "calendario": {
        "etiqueta": "Universidad",
        "titulo": "Calendario",
        "subtitulo": "Tus tareas y eventos del mes.",
    },
    "asistencia": {
        "etiqueta": "Universidad",
        "titulo": "Asistencia",
        "subtitulo": "Las horas de clase a las que has ido en cada materia, según lo que marcas en el horario.",
    },
}

# ---- Encabezados en Deporte (mismas páginas, con sus propios datos) ----
PAGINAS_DEPORTE = {
    "horario": {
        "etiqueta": "Deporte",
        "titulo": "Horario de entrenos",
        "subtitulo": "Tus entrenamientos de 8:00 a 20:00, si fuiste y lo que te toca hacer.",
    },
    "tareas": {
        "etiqueta": "Deporte",
        "titulo": "Metas",
        "subtitulo": "Las metas que quieres alcanzar esta semana. Salen en el calendario el día que elijas.",
    },
    "pendientes": {
        "etiqueta": "Deporte",
        "titulo": "Pendientes",
        "subtitulo": "Lo que falta por hacer, ordenado por fecha.",
    },
    "calendario": {
        "etiqueta": "Deporte",
        "titulo": "Calendario",
        "subtitulo": "Tus partidos, competiciones y metas del mes.",
    },
    "asistencia": {
        "etiqueta": "Deporte",
        "titulo": "Alimentación e info",
        "subtitulo": "Tu objetivo de calorías y macros, lo que comes en cada comida, tu IMC y cómo va tu semana.",
    },
}

# ---- Tipos de entreno (solo en Deporte) ----
# Al añadir algo al calendario o al horario en Deporte se elige uno de estos.
# (clave que se guarda en la base de datos, nombre que se ve)
TIPOS_DEPORTE = [
    ("entrenamiento", "Entrenamiento"),
    ("descarga", "Descarga"),
    ("rehabilitacion", "Rehabilitación"),
    ("comida", "Comida"),
    ("cardio", "Cardio"),
    ("fuerza", "Entrenamiento de fuerza"),
]
NOMBRE_TIPO_DEPORTE = dict(TIPOS_DEPORTE)

# Comidas del día en "Alimentación e info" (Deporte): (clave, nombre)
TIPOS_COMIDA = [
    ("desayuno", "Desayuno"),
    ("almuerzo", "Almuerzo"),
    ("cena", "Cena"),
    ("snack", "Snack"),
]

# ---- Palabras que cambian según el calendario ----
# En Universidad se habla de tareas y materias; en Deporte, de metas y deportes.
PALABRAS = {
    "universidad": {
        "tarea": "tarea", "Tarea": "Tarea", "tareas": "tareas", "Tareas": "Tareas",
        "materia": "Materia", "sin_materia": "Sin materia", "clase": "clase",
        "pregunta": "¿Qué tienes que hacer?", "ejemplo": "ej: Guía de ejercicios 3",
        "fecha": "Fecha de entrega", "entrega": "Entrega", "boton": "Agregar tarea",
        "vacio": "Todavía no hay tareas.", "completadas": "Tareas completadas", "hechas": "Tareas hechas",
        "proximas": "Próximas tareas", "dejaron": "+ ¿Dejaron tarea?", "anadir": "Añadir a Tareas",
        "era": "¿Era una de tus tareas? (se marcará como hecha)",
        "sin_materias": "Para elegir una materia, primero agrega tus clases en el",
    },
    "deporte": {
        "tarea": "meta", "Tarea": "Meta", "tareas": "metas", "Tareas": "Metas",
        "materia": "Actividad", "sin_materia": "Sin actividad", "clase": "entreno",
        "pregunta": "¿Qué meta quieres alcanzar?", "ejemplo": "ej: Correr 15 km en la semana",
        "fecha": "Para el día (esta semana)", "entrega": "Para el", "boton": "Agregar meta",
        "vacio": "Todavía no hay metas.", "completadas": "Metas cumplidas", "hechas": "Metas cumplidas",
        "proximas": "Próximas metas", "dejaron": "+ ¿Nueva meta?", "anadir": "Añadir a Metas",
        "era": "¿Era una de tus metas? (se marcará como cumplida)",
        "sin_materias": "Para elegir un deporte, primero agrega tus entrenos en",
    },
}

# ---- Portada (hero) de la página de inicio ----
INICIO = {
    "saludo": "Hola",
    "bienvenida": "bienvenido",  # el título queda: "Hola seb, bienvenido"
    "subtitulo": "Organiza tus clases, tareas y asistencias de hoy",
    "boton_principal": {"texto": "Ver pendientes", "ruta": "pendientes"},
    "boton_secundario": {"texto": "Ver horario", "ruta": "horario"},
    "titulo_resumen": "Tu día",
    "anadir_nombre": "Añade tu nombre",
}

# ---- Página de contraseña ----
ENTRAR = {
    "titulo": "Bienvenido de vuelta",
    "subtitulo": "Entra con tu usuario y tu contraseña.",
    "boton": "Entrar",
    "error": "Usuario o contraseña incorrectos.",
    "sin_cuenta": "¿No tienes cuenta?",
    "ir_registro": "Crear una cuenta",
}

# ---- Página "Mi cuenta" ----
CUENTA = {
    "etiqueta": "Mi perfil",
    "titulo": "Mis datos",
    "subtitulo": "Cambia tu nombre o tu contraseña.",
}

# ---- Página "Mi perfil" ----
PERFIL = {
    "etiqueta": "Cuenta",
    "titulo": "Mi perfil",
    "datos_titulo": "Mis datos",
    "datos_texto": "Cambia tu nombre, tu apellido o tu contraseña.",
    "avances_titulo": "Mis avances",
    "avances_texto": "Mira tu asistencia y las tareas que has cumplido.",
    "ajustes_titulo": "Ajustes",
    "ajustes_texto": "Elige el color de la web.",
}

# ---- Página "Mis avances" ----
AVANCES = {
    "etiqueta": "Mi perfil",
    "titulo": "Mis avances",
    "subtitulo": "Tu asistencia y tus tareas cumplidas.",
}

# ---- Página para crear una cuenta ----
REGISTRAR = {
    "titulo": "Crea tu cuenta",
    "subtitulo": "Necesitas el código de invitación que te pasó quien te invitó.",
    "subtitulo_sin_codigo": "Elige un usuario y una contraseña.",
    "boton": "Crear cuenta",
    "con_cuenta": "¿Ya tienes cuenta?",
    "ir_entrar": "Entrar",
    "ayuda_nombre": "De 3 a 30 letras o números, sin espacios (también vale . _ -).",
    "ayuda_clave": "Mínimo 8 caracteres.",
    "error_codigo": "El código de invitación no es correcto.",
    "error_nombre_real": "Escribe tu nombre y tu apellido.",
    "error_nombre": "El usuario debe tener de 3 a 30 letras o números, sin espacios.",
    "error_nombre_usado": "Ese usuario ya existe. Elige otro.",
    "error_clave_corta": "La contraseña debe tener al menos 8 caracteres.",
    "error_claves_distintas": "Las dos contraseñas no coinciden.",
    "bienvenida": "¡Cuenta creada! Empieza agregando tus clases en el horario.",
}

# ---- Mensajes cuando algo se guarda (aparecen en un panel arriba) ----
MENSAJES = {
    "clase": "Clase agregada al horario.",
    "actividad_extra": "Actividad agregada al horario.",
    "clase_editada": "Cambios guardados.",
    "tarea": "Tarea guardada.",
    "meta": "Meta guardada.",
    "actividad": "Actividad de asistencia guardada.",
    "color": "Color guardado.",
    "color_invalido": "Ese color no es válido.",
    "modo_universidad": "Ahora usas el calendario de Universidad.",
    "modo_deporte": "Ahora usas el calendario de Deporte. Sus datos van aparte de los de Universidad.",
    "actividad_tarea": "Actividad guardada y tarea marcada como hecha.",
    "cuenta": "Nombre guardado.",
    "clave": "Contraseña cambiada.",
    "evento": "Evento agregado al calendario.",
    "comida": "Alimento añadido.",
    "objetivo": "Objetivo de calorías guardado.",
    "porcentajes_ajustados": "Los porcentajes no sumaban 100 %, así que los ajusté manteniendo la proporción.",
    "examen": "Examen agregado al calendario.",
    "eventos_subidos": "Listo: {nuevos} evento(s) añadido(s) a {nombre}. Ya los ves en el calendario.",
    "eventos_repetidos": " ({repetidos} ya estaban y no se repitieron.)",
    "eventos_problemas": " Ojo: {cuantos} fila(s) no se entendieron ({primera})",
    "eventos_vacio": "No encontré eventos en el documento. Revisa que tenga fecha, hora, nombre y tipo.",
    "eventos_grande": "El documento es demasiado grande (máximo 2 MB).",
    "calendario_borrado": "Calendario de eventos borrado.",
    "campo_obligatorio": "Este campo es obligatorio.",
    "numero_invalido": "Escribe un número mayor o igual a 0.",
}

# ---- Footer: 4 columnas de enlaces ----
FOOTER = [
    {"titulo": "Clases", "enlaces": [("Horario", "horario"), ("Asistencia", "asistencia")]},
    {"titulo": "Tareas", "enlaces": [("Tareas", "tareas"), ("Calendario", "calendario_vista"),
                                     ("Pendientes", "pendientes")]},
    {"titulo": "Accesos rápidos", "enlaces": [("Nueva tarea", "tareas"),
                                              ("Marcar asistencia", "horario"), ("Mi perfil", "perfil")]},
    {"titulo": "Hoy", "enlaces": [("Clases de hoy", "horario"), ("Lo pendiente", "pendientes"),
                                  ("Mes actual", "calendario_vista")]},
]
COPYRIGHT = "weblife · Hecha con Python y Flask"
# Nota pequeña que sale en "Seleccionar evento"
NOTA_EXAMENES = ("Si hace falta una o más materias, revisa el horario oficial de tu universidad "
                 "y súbelas con \"Añade tus eventos\".")


def todo(modo="universidad"):
    """Junta todos los textos en un diccionario para las plantillas."""
    return {
        "nombre_sitio": NOMBRE_SITIO,
        "menu": menu(modo),
        "p": PALABRAS["deporte" if modo == "deporte" else "universidad"],
        "boton_menu": BOTON_MENU,
        "texto_salir": TEXTO_SALIR,
        "paginas": PAGINAS_DEPORTE if modo == "deporte" else PAGINAS,
        "tipos_deporte": TIPOS_DEPORTE, "nombre_tipo_deporte": NOMBRE_TIPO_DEPORTE,
        "tipos_comida": TIPOS_COMIDA,
        "inicio": INICIO,
        "entrar": ENTRAR,
        "registrar": REGISTRAR,
        "cuenta": CUENTA,
        "perfil": PERFIL,
        "avances": AVANCES,
        "mensajes": MENSAJES,
        "footer": FOOTER,
        "copyright": COPYRIGHT,
        "nota_examenes": NOTA_EXAMENES,
    }
