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
    ("Calendario", "calendario_vista"),
    ("Pendientes", "pendientes"),
    ("Alimentación", "alimentacion"),
    ("Entrenamiento", "entrenamiento"),
    ("Pasos", "pasos"),
]

# Botón en píldora a la derecha del menú
BOTON_MENU = {"texto": "Nueva tarea", "ruta": "tareas"}
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
    "alimentacion": {
        "etiqueta": "Vida",
        "titulo": "Alimentación",
        "subtitulo": "Lo que comes cada día y sus calorías.",
    },
    "entrenamiento": {
        "etiqueta": "Vida",
        "titulo": "Entrenamiento",
        "subtitulo": "Tus sesiones de ejercicio y cuánto duraron.",
    },
    "pasos": {
        "etiqueta": "Vida",
        "titulo": "Pasos diarios",
        "subtitulo": "Tus pasos de la última semana frente a tu meta.",
    },
}

# ---- Portada (hero) de la página de inicio ----
INICIO = {
    "saludo": "Hola, hoy es",
    "subtitulo": "Tu universidad y tu vida diaria, organizadas en un solo lugar.",
    "boton_principal": {"texto": "Ver pendientes", "ruta": "pendientes"},
    "boton_secundario": {"texto": "Ver horario", "ruta": "horario"},
    "titulo_resumen": "Tu día",
}

# ---- Página de contraseña ----
ENTRAR = {
    "titulo": "Bienvenido de vuelta",
    "subtitulo": "Escribe tu contraseña para entrar a weblife.",
    "boton": "Entrar",
    "error": "Contraseña incorrecta",
}

# ---- Mensajes cuando algo se guarda (aparecen en un panel arriba) ----
MENSAJES = {
    "clase": "Clase agregada al horario.",
    "tarea": "Tarea guardada.",
    "evento": "Evento agregado al calendario.",
    "comida": "Comida registrada.",
    "entrenamiento": "Entrenamiento registrado.",
    "pasos": "Pasos guardados.",
    "campo_obligatorio": "Este campo es obligatorio.",
    "numero_invalido": "Escribe un número mayor o igual a 0.",
}

# ---- Footer: 4 columnas de enlaces ----
FOOTER = [
    {"titulo": "Universidad", "enlaces": [("Horario", "horario"), ("Tareas", "tareas"),
                                          ("Calendario", "calendario_vista"), ("Pendientes", "pendientes")]},
    {"titulo": "Vida", "enlaces": [("Alimentación", "alimentacion"), ("Entrenamiento", "entrenamiento"),
                                   ("Pasos", "pasos")]},
    {"titulo": "Accesos rápidos", "enlaces": [("Inicio", "inicio"), ("Nueva tarea", "tareas"),
                                              ("Registrar pasos", "pasos")]},
    {"titulo": "Hoy", "enlaces": [("Clases de hoy", "horario"), ("Lo pendiente", "pendientes"),
                                  ("Mes actual", "calendario_vista")]},
]
COPYRIGHT = "weblife · Hecha con Python y Flask"


def todo():
    """Junta todos los textos en un diccionario para las plantillas."""
    return {
        "nombre_sitio": NOMBRE_SITIO,
        "menu": MENU,
        "boton_menu": BOTON_MENU,
        "texto_salir": TEXTO_SALIR,
        "paginas": PAGINAS,
        "inicio": INICIO,
        "entrar": ENTRAR,
        "mensajes": MENSAJES,
        "footer": FOOTER,
        "copyright": COPYRIGHT,
    }
