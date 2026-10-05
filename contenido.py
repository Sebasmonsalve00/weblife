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
    "asistencia": {
        "etiqueta": "Universidad",
        "titulo": "Asistencia",
        "subtitulo": "Las horas de clase a las que has ido en cada materia, según lo que marcas en el horario.",
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
    "etiqueta": "Cuenta",
    "titulo": "Mi cuenta",
    "subtitulo": "Tu nombre aparece en el saludo de la página de inicio.",
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
    "tarea": "Tarea guardada.",
    "actividad": "Actividad de asistencia guardada.",
    "cuenta": "Nombre guardado.",
    "examenes": "Fechas de examen cargadas: {} nuevas en tu calendario.",
    "evento": "Evento agregado al calendario.",
    "campo_obligatorio": "Este campo es obligatorio.",
    "numero_invalido": "Escribe un número mayor o igual a 0.",
}

# ---- Footer: 4 columnas de enlaces ----
FOOTER = [
    {"titulo": "Clases", "enlaces": [("Horario", "horario"), ("Asistencia", "asistencia")]},
    {"titulo": "Tareas", "enlaces": [("Tareas", "tareas"), ("Calendario", "calendario_vista"),
                                     ("Pendientes", "pendientes")]},
    {"titulo": "Accesos rápidos", "enlaces": [("Inicio", "inicio"), ("Nueva tarea", "tareas"),
                                              ("Marcar asistencia", "horario"), ("Mi cuenta", "cuenta")]},
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
        "registrar": REGISTRAR,
        "cuenta": CUENTA,
        "mensajes": MENSAJES,
        "footer": FOOTER,
        "copyright": COPYRIGHT,
    }
