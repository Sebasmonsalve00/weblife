# ============================================================
#  examenes.py - Calendarios oficiales de exámenes
#
#  Organizado así:  carrera  ->  curso  ->  convocatoria  ->  lista de exámenes
#  Cada examen es: (asignatura, fecha "AAAA-MM-DD", hora "HH:MM" o None si no tiene, último dato de la tabla)
#
#  Para agregar otra carrera, curso o convocatoria, copia un bloque
#  y cambia los datos. La página del calendario los muestra sola.
# ============================================================

CALENDARIOS = {
    "Grado en Marketing": {
        "2º Curso": {
            "Diciembre 2026": [
                # Ética I: la tabla dice "detalle en enlace fila 6" (sin fecha), por eso no está.
                ("Corporate Communication", "2026-12-02", "16:00", "6"),
                ("Desarrollo Personal y Liderazgo", "2026-12-18", None, ""),   # sin hora en la tabla
                ("Gestión de Marketing", "2026-12-04", "16:00", "6"),
                ("Introducción a la Microeconomía", "2026-12-14", "16:00", "Ed. Amigos - Aula 10"),
                ("Introduction to Branding", "2026-12-16", "16:00", "6"),
                ("Métodos de innovación", "2026-12-10", "16:00", "6"),
            ],
        },
        "3º Curso": {
            "Diciembre 2026": [
                ("Brand Management", "2026-12-07", "12:00", "5"),
                ("Criterios publicitarios", "2026-12-11", "12:00", "6"),
                ("Diseño e Innovación de Producto", "2026-12-15", "12:00", "6"),
                ("Finanzas para marketing", "2026-12-09", "12:00", "6"),
                ("Investigación de mercados I", "2026-12-01", "12:00", "6"),
                ("Team Management", "2026-12-04", "12:00", "6"),
            ],
            # "Mayo 2027": [ ... ],   <- se agrega cuando lleguen las fechas
        },
    },
    "Grado en Periodismo": {
        "2º Curso": {
            "Diciembre 2026": [
                # Ética y persona: "detalle en enlace fila 6" (sin fecha), no está.
                # International Communication and Public Opinion (2º Global): "Web Derecho" (sin fecha), no está.
                ("International Journalism", "2026-12-04", "16:00", "4"),
                ("Teoría del periodismo", "2026-12-11", "16:00", "4"),
                ("La entrevista y el perfil periodístico", "2026-12-02", "16:00", "4"),
                ("Sistemas políticos", "2026-12-16", "16:00", "3"),
                ("Cultura periodística", "2026-12-14", "09:00", "2 y 5"),
            ],
        },
        "3º Curso": {
            "Diciembre 2026": [
                ("Fundamentos de periodismo económico", "2026-12-07", "12:00", "4"),
                ("Géneros y edición de diarios y revistas", "2026-12-16", "12:00", "5"),
                ("Géneros y programas de radio", "2026-12-10", "12:00", "5"),
                ("Media and Politics", "2026-12-02", "12:00", "11"),
                ("Medios de comunicación y política en la España reciente", "2026-12-02", "12:00", "3"),
            ],
        },
    },
}


# La universidad de estos calendarios (en "Seleccionar evento" se elige universidad, año, carrera y convocatoria).
# Al arrancar, la web los copia a la base de datos (ver crear_tablas en app.py) junto a los que suben los usuarios.
UNIVERSIDAD = "Universidad de Navarra"

# Sugerencias para "Añade tus eventos" (puedes agregar más).
CURSOS = ["1º Curso", "2º Curso", "3º Curso", "4º Curso"]
CONVOCATORIAS = ["Diciembre 2026", "Mayo 2027", "Junio 2027"]


def examenes(carrera, curso, convocatoria):
    """Devuelve la lista de exámenes de esa opción, o una lista vacía si no existe."""
    return CALENDARIOS.get(carrera, {}).get(curso, {}).get(convocatoria, [])
