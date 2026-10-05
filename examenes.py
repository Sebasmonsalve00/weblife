# ============================================================
#  examenes.py - Calendarios oficiales de exámenes
#
#  Organizado así:  carrera  ->  curso  ->  convocatoria  ->  lista de exámenes
#  Cada examen es: (asignatura, fecha "AAAA-MM-DD", hora "HH:MM", último dato de la tabla)
#
#  Para agregar otra carrera, curso o convocatoria, copia un bloque
#  y cambia los datos. La página del calendario los muestra sola.
# ============================================================

CALENDARIOS = {
    "Grado en Marketing": {
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
}


def examenes(carrera, curso, convocatoria):
    """Devuelve la lista de exámenes de esa opción, o una lista vacía si no existe."""
    return CALENDARIOS.get(carrera, {}).get(curso, {}).get(convocatoria, [])
