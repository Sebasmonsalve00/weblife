# ============================================================
#  weblife - Mi página personal
#  Secciones:
#    - Universidad: horario, tareas, calendario y pendientes
#    - Vida: alimentación, entrenamiento y pasos diarios
#
#  Para ejecutarla:  python app.py
#  Luego abre en el navegador:  http://127.0.0.1:5000
# ============================================================

import calendar
import hmac
import os
import sqlite3
import time
from datetime import date, timedelta

from flask import Flask, redirect, render_template, request, session, url_for

# Creamos la aplicación web. "__name__" le dice a Flask dónde está este archivo.
app = Flask(__name__)

# Carpeta donde está este archivo. La usamos para que la base de datos
# siempre quede al lado de app.py, la ejecutes desde donde la ejecutes.
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Archivo donde se guardan todos los datos. Se crea solo la primera vez.
ARCHIVO_BD = os.path.join(CARPETA, "weblife.db")

# ------------------------------------------------------------
#  Contraseña
#  Se leen de "variables de entorno" para no escribirlas en el código.
#  - WEBLIFE_CLAVE: la contraseña para entrar a tu web.
#  - WEBLIFE_SECRETO: un texto largo y aleatorio que Flask usa para
#    firmar la "cookie" que recuerda que ya iniciaste sesión.
#  Si no existen (en tu computador), la web funciona sin contraseña.
# ------------------------------------------------------------
CLAVE = os.environ.get("WEBLIFE_CLAVE", "")
app.secret_key = os.environ.get("WEBLIFE_SECRETO", "solo-para-tu-computador")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"           # protege los formularios
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = bool(CLAVE)       # la cookie solo viaja por https
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)  # recordarte 30 días

# Nombres en español (Python los da en inglés por defecto).
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# Meta diaria de pasos. ¡Cámbiala si quieres!
META_PASOS = 10000


# ------------------------------------------------------------
#  Base de datos
# ------------------------------------------------------------

def conectar():
    """Abre una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(ARCHIVO_BD)
    # Esto permite leer las columnas por nombre: fila["titulo"]
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():
    """Crea las tablas si todavía no existen."""
    conexion = conectar()
    conexion.executescript("""
        CREATE TABLE IF NOT EXISTS clases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            dia INTEGER NOT NULL,          -- 0 = lunes ... 6 = domingo
            hora_inicio TEXT NOT NULL,     -- "08:00"
            hora_fin TEXT NOT NULL,
            sala TEXT
        );

        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            materia TEXT,
            fecha_entrega TEXT NOT NULL,   -- "2026-10-05"
            hecha INTEGER NOT NULL DEFAULT 0   -- 0 = pendiente, 1 = hecha
        );

        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT
        );

        CREATE TABLE IF NOT EXISTS comidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,            -- desayuno, almuerzo, cena, snack
            descripcion TEXT NOT NULL,
            calorias INTEGER
        );

        CREATE TABLE IF NOT EXISTS entrenamientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL,            -- pesas, correr, fútbol...
            minutos INTEGER,
            notas TEXT
        );

        CREATE TABLE IF NOT EXISTS pasos (
            fecha TEXT PRIMARY KEY,        -- un solo registro por día
            cantidad INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS asistencias (
            clase_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,           -- el día de esa clase
            asistio INTEGER NOT NULL,      -- 1 = fui, 0 = no fui
            PRIMARY KEY (clase_id, fecha)  -- una sola marca por clase y día
        );
    """)

    # Las tablas creadas antes no tenían "fecha_creacion" en tareas: la agregamos.
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(tareas)")]
    if "fecha_creacion" not in columnas:
        conexion.execute("ALTER TABLE tareas ADD COLUMN fecha_creacion TEXT")
    conexion.commit()
    conexion.close()


def consultar(sql, parametros=()):
    """Ejecuta un SELECT y devuelve la lista de filas."""
    conexion = conectar()
    filas = conexion.execute(sql, parametros).fetchall()
    conexion.close()
    return filas


def modificar(sql, parametros=()):
    """Ejecuta un INSERT, UPDATE o DELETE y guarda los cambios."""
    conexion = conectar()
    conexion.execute(sql, parametros)
    conexion.commit()
    conexion.close()


# ------------------------------------------------------------
#  Inicio de sesión
# ------------------------------------------------------------

@app.before_request
def pedir_contrasena():
    """Se ejecuta antes de cada página: si hay contraseña y no has entrado, te manda al login."""
    if not CLAVE:
        return None  # sin contraseña configurada: acceso libre (tu computador)
    if session.get("dentro") or request.endpoint in ("entrar", "static"):
        return None
    return redirect(url_for("entrar"))


@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    error = None
    if request.method == "POST":
        # compare_digest compara de forma segura (no revela pistas por el tiempo que tarda)
        if CLAVE and hmac.compare_digest(request.form["clave"].encode(), CLAVE.encode()):
            session["dentro"] = True
            session.permanent = True
            return redirect(url_for("inicio"))
        time.sleep(1)  # frena a quien intente adivinar la contraseña muchas veces
        error = "Contraseña incorrecta"
    return render_template("entrar.html", error=error)


@app.route("/salir", methods=["POST"])
def salir():
    session.clear()
    return redirect(url_for("entrar"))


# ------------------------------------------------------------
#  Página de inicio (resumen del día)
# ------------------------------------------------------------

@app.route("/")
def inicio():
    hoy = date.today()
    hoy_texto = hoy.isoformat()  # "2026-10-05"

    clases_hoy = consultar(
        "SELECT * FROM clases WHERE dia = ? ORDER BY hora_inicio", (hoy.weekday(),))
    pendientes = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 ORDER BY fecha_entrega LIMIT 5")
    fila_pasos = consultar("SELECT cantidad FROM pasos WHERE fecha = ?", (hoy_texto,))
    pasos_hoy = fila_pasos[0]["cantidad"] if fila_pasos else 0
    fila_cal = consultar(
        "SELECT SUM(calorias) AS total FROM comidas WHERE fecha = ?", (hoy_texto,))
    calorias_hoy = fila_cal[0]["total"] or 0

    return render_template(
        "inicio.html",
        hoy=hoy_texto,
        dia_nombre=DIAS_SEMANA[hoy.weekday()],
        clases_hoy=clases_hoy,
        pendientes=pendientes,
        pasos_hoy=pasos_hoy,
        meta_pasos=META_PASOS,
        calorias_hoy=calorias_hoy,
    )


# ------------------------------------------------------------
#  UNIVERSIDAD: Horario semanal de clases
# ------------------------------------------------------------

# El horario se dibuja de 8:00 a 20:00. Cada hora mide 60 píxeles de alto.
HORA_INICIO_DIA = 8
HORA_FIN_DIA = 20
PIXELES_POR_HORA = 60


def a_minutos(hora_texto):
    """Convierte "09:30" en minutos desde medianoche: 9 * 60 + 30 = 570."""
    horas, minutos = hora_texto.split(":")
    return int(horas) * 60 + int(minutos)


@app.route("/universidad/horario", methods=["GET", "POST"])
def horario():
    error = None
    # Si se envió el formulario (POST), guardamos la clase nueva.
    if request.method == "POST":
        inicio = request.form["hora_inicio"]
        fin = request.form["hora_fin"]
        if a_minutos(fin) <= a_minutos(inicio):
            error = "La hora de término tiene que ser después de la hora de inicio."
        else:
            modificar(
                "INSERT INTO clases (nombre, dia, hora_inicio, hora_fin, sala) VALUES (?, ?, ?, ?, ?)",
                (request.form["nombre"], int(request.form["dia"]), inicio, fin, request.form["sala"]),
            )
            return redirect(url_for("horario"))

    # Todas las clases ordenadas por día y luego por hora.
    clases = consultar("SELECT * FROM clases ORDER BY dia, hora_inicio")

    # ---- Panel lateral: las clases de un día (por defecto, hoy) ----
    try:
        dia_panel = date.fromisoformat(request.args.get("fecha", ""))
    except ValueError:
        dia_panel = date.today()
    texto_panel = dia_panel.isoformat()
    marcas = {fila["clase_id"]: fila["asistio"] for fila in
              consultar("SELECT * FROM asistencias WHERE fecha = ?", (texto_panel,))}
    panel = []
    for clase in clases:
        if clase["dia"] == dia_panel.weekday():
            pendientes_materia = consultar(
                "SELECT * FROM tareas WHERE materia = ? AND hecha = 0 ORDER BY fecha_entrega",
                (clase["nombre"],))
            panel.append({"clase": clase, "asistio": marcas.get(clase["id"]),
                          "pendientes": pendientes_materia})

    # Calculamos dónde va cada clase en la grilla:
    # "arriba" = cuántos píxeles desde las 8:00, "alto" = cuánto dura.
    limite_arriba = HORA_INICIO_DIA * 60
    limite_abajo = HORA_FIN_DIA * 60
    por_dia = {numero: [] for numero in range(7)}
    for clase in clases:
        inicio = max(a_minutos(clase["hora_inicio"]), limite_arriba)
        fin = min(a_minutos(clase["hora_fin"]), limite_abajo)
        if fin <= inicio:
            continue  # la clase queda fuera de 8:00-20:00, no se dibuja
        por_dia[clase["dia"]].append({
            "clase": clase,
            "arriba": (inicio - limite_arriba) * PIXELES_POR_HORA // 60,
            "alto": (fin - inicio) * PIXELES_POR_HORA // 60,
        })

    # De lunes a viernes siempre; sábado y domingo solo si tienen clases.
    dias_visibles = [d for d in range(7) if d < 5 or por_dia[d]]
    horas = [f"{h:02d}:00" for h in range(HORA_INICIO_DIA, HORA_FIN_DIA + 1)]

    return render_template(
        "horario.html", dias=DIAS_SEMANA, dias_visibles=dias_visibles, por_dia=por_dia,
        clases=clases, horas=horas, alto_total=(HORA_FIN_DIA - HORA_INICIO_DIA) * PIXELES_POR_HORA,
        pixeles_hora=PIXELES_POR_HORA, error=error,
        panel=panel, dia_panel=texto_panel, nombre_dia_panel=DIAS_SEMANA[dia_panel.weekday()],
        es_hoy=(dia_panel == date.today()),
        dia_anterior=(dia_panel - timedelta(days=1)).isoformat(),
        dia_siguiente=(dia_panel + timedelta(days=1)).isoformat(),
        entrega_sugerida=(dia_panel + timedelta(days=7)).isoformat(),
    )


@app.route("/universidad/horario/borrar/<int:id>", methods=["POST"])
def borrar_clase(id):
    modificar("DELETE FROM clases WHERE id = ?", (id,))
    modificar("DELETE FROM asistencias WHERE clase_id = ?", (id,))
    return redirect(url_for("horario"))


@app.route("/universidad/horario/asistencia/<int:id>", methods=["POST"])
def marcar_asistencia(id):
    """Guarda si fuiste (1) o no (0) a una clase en un día. Si vuelves a apretar el mismo botón, se borra."""
    fecha = request.form["fecha"]
    asistio = int(request.form["asistio"])
    anterior = consultar("SELECT asistio FROM asistencias WHERE clase_id = ? AND fecha = ?", (id, fecha))
    if anterior and anterior[0]["asistio"] == asistio:
        modificar("DELETE FROM asistencias WHERE clase_id = ? AND fecha = ?", (id, fecha))
    else:
        modificar("INSERT OR REPLACE INTO asistencias (clase_id, fecha, asistio) VALUES (?, ?, ?)",
                  (id, fecha, asistio))
    return redirect(url_for("horario", fecha=fecha))


@app.route("/universidad/horario/tarea/<int:id>", methods=["POST"])
def tarea_rapida(id):
    """Agrega una tarea desde el panel del horario, con la materia de esa clase."""
    clase = consultar("SELECT nombre FROM clases WHERE id = ?", (id,))
    if clase:
        guardar_tarea(request.form["titulo"], clase[0]["nombre"], request.form["fecha_entrega"])
    return redirect(url_for("horario", fecha=request.form["fecha"]))


# ------------------------------------------------------------
#  UNIVERSIDAD: Tareas
# ------------------------------------------------------------

def guardar_tarea(titulo, materia, fecha_entrega):
    """Guarda una tarea nueva con la fecha de hoy como fecha de creación."""
    modificar(
        "INSERT INTO tareas (titulo, materia, fecha_entrega, fecha_creacion) VALUES (?, ?, ?, ?)",
        (titulo, materia, fecha_entrega, date.today().isoformat()),
    )


@app.route("/universidad/tareas", methods=["GET", "POST"])
def tareas():
    if request.method == "POST":
        guardar_tarea(request.form["titulo"], request.form["materia"], request.form["fecha_entrega"])
        return redirect(url_for("tareas"))

    todas = consultar("SELECT * FROM tareas ORDER BY hecha, fecha_entrega")
    # Las materias salen de las clases del horario (sin repetir y en orden alfabético).
    materias = [fila["nombre"] for fila in
                consultar("SELECT DISTINCT nombre FROM clases ORDER BY nombre")]
    return render_template("tareas.html", tareas=todas, materias=materias,
                           hoy=date.today().isoformat())


@app.route("/universidad/tareas/cambiar/<int:id>", methods=["POST"])
def cambiar_tarea(id):
    # "1 - hecha" cambia 0 por 1 y 1 por 0 (marcar / desmarcar).
    modificar("UPDATE tareas SET hecha = 1 - hecha WHERE id = ?", (id,))
    # Volvemos a la página desde donde se hizo clic.
    return redirect(request.referrer or url_for("tareas"))


@app.route("/universidad/tareas/borrar/<int:id>", methods=["POST"])
def borrar_tarea(id):
    modificar("DELETE FROM tareas WHERE id = ?", (id,))
    return redirect(request.referrer or url_for("tareas"))


# ------------------------------------------------------------
#  UNIVERSIDAD: Pendientes
# ------------------------------------------------------------

@app.route("/universidad/pendientes")
def pendientes():
    hoy = date.today().isoformat()
    en_7_dias = (date.today() + timedelta(days=7)).isoformat()

    # Las fechas "AAAA-MM-DD" se pueden comparar como texto. ¡Truco útil!
    atrasadas = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND fecha_entrega < ? ORDER BY fecha_entrega", (hoy,))
    esta_semana = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND fecha_entrega BETWEEN ? AND ? ORDER BY fecha_entrega",
        (hoy, en_7_dias))
    despues = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND fecha_entrega > ? ORDER BY fecha_entrega", (en_7_dias,))

    return render_template("pendientes.html", atrasadas=atrasadas,
                           esta_semana=esta_semana, despues=despues)


# ------------------------------------------------------------
#  UNIVERSIDAD: Calendario mensual
# ------------------------------------------------------------

@app.route("/universidad/calendario", methods=["GET", "POST"])
def calendario_vista():
    # Agregar un evento (examen, reunión, etc.)
    if request.method == "POST":
        modificar("INSERT INTO eventos (titulo, fecha, hora) VALUES (?, ?, ?)",
                  (request.form["titulo"], request.form["fecha"], request.form["hora"]))
        fecha = date.fromisoformat(request.form["fecha"])
        return redirect(url_for("calendario_vista", anio=fecha.year, mes=fecha.month))

    # El mes a mostrar viene en la URL: /universidad/calendario?anio=2026&mes=10
    hoy = date.today()
    anio = request.args.get("anio", hoy.year, type=int)
    mes = request.args.get("mes", hoy.month, type=int)

    # calendar.monthcalendar devuelve las semanas del mes como listas de números.
    # Los días que no son de ese mes vienen como 0.
    semanas = calendar.monthcalendar(anio, mes)

    # Buscamos tareas y eventos de este mes. "2026-10%" = todo octubre 2026.
    patron = f"{anio}-{mes:02d}-%"
    cosas_por_dia = {}
    for tarea in consultar("SELECT * FROM tareas WHERE fecha_entrega LIKE ?", (patron,)):
        dia = int(tarea["fecha_entrega"][8:10])
        cosas_por_dia.setdefault(dia, []).append(
            {"texto": tarea["titulo"], "tipo": "tarea", "hecha": tarea["hecha"]})
    for evento in consultar("SELECT * FROM eventos WHERE fecha LIKE ? ORDER BY hora", (patron,)):
        dia = int(evento["fecha"][8:10])
        texto = f"{evento['hora']} {evento['titulo']}" if evento["hora"] else evento["titulo"]
        cosas_por_dia.setdefault(dia, []).append(
            {"texto": texto, "tipo": "evento", "id": evento["id"]})

    # Mes anterior y siguiente para los botones ◀ ▶
    mes_anterior = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    mes_siguiente = (anio, mes + 1) if mes < 12 else (anio + 1, 1)

    return render_template(
        "calendario.html",
        semanas=semanas, anio=anio, mes=mes, nombre_mes=MESES[mes],
        dias=DIAS_SEMANA, cosas_por_dia=cosas_por_dia,
        hoy=hoy, mes_anterior=mes_anterior, mes_siguiente=mes_siguiente,
    )


@app.route("/universidad/calendario/borrar/<int:id>", methods=["POST"])
def borrar_evento(id):
    modificar("DELETE FROM eventos WHERE id = ?", (id,))
    return redirect(request.referrer or url_for("calendario_vista"))


# ------------------------------------------------------------
#  VIDA: Alimentación
# ------------------------------------------------------------

@app.route("/vida/alimentacion", methods=["GET", "POST"])
def alimentacion():
    if request.method == "POST":
        # Las calorías son opcionales: si el campo viene vacío guardamos None.
        calorias = request.form["calorias"]
        modificar(
            "INSERT INTO comidas (fecha, tipo, descripcion, calorias) VALUES (?, ?, ?, ?)",
            (request.form["fecha"], request.form["tipo"], request.form["descripcion"],
             int(calorias) if calorias else None),
        )
        return redirect(url_for("alimentacion"))

    comidas = consultar("SELECT * FROM comidas ORDER BY fecha DESC, id DESC LIMIT 50")
    # Total de calorías por día, para los últimos 7 días con registros.
    totales = consultar("""
        SELECT fecha, SUM(calorias) AS total, COUNT(*) AS cantidad
        FROM comidas GROUP BY fecha ORDER BY fecha DESC LIMIT 7
    """)
    return render_template("alimentacion.html", comidas=comidas, totales=totales,
                           hoy=date.today().isoformat())


@app.route("/vida/alimentacion/borrar/<int:id>", methods=["POST"])
def borrar_comida(id):
    modificar("DELETE FROM comidas WHERE id = ?", (id,))
    return redirect(url_for("alimentacion"))


# ------------------------------------------------------------
#  VIDA: Entrenamiento
# ------------------------------------------------------------

@app.route("/vida/entrenamiento", methods=["GET", "POST"])
def entrenamiento():
    if request.method == "POST":
        minutos = request.form["minutos"]
        modificar(
            "INSERT INTO entrenamientos (fecha, tipo, minutos, notas) VALUES (?, ?, ?, ?)",
            (request.form["fecha"], request.form["tipo"],
             int(minutos) if minutos else None, request.form["notas"]),
        )
        return redirect(url_for("entrenamiento"))

    lista = consultar("SELECT * FROM entrenamientos ORDER BY fecha DESC, id DESC LIMIT 50")
    hace_7_dias = (date.today() - timedelta(days=6)).isoformat()
    semana = consultar(
        "SELECT COUNT(*) AS sesiones, SUM(minutos) AS minutos FROM entrenamientos WHERE fecha >= ?",
        (hace_7_dias,))[0]
    return render_template("entrenamiento.html", entrenamientos=lista, semana=semana,
                           hoy=date.today().isoformat())


@app.route("/vida/entrenamiento/borrar/<int:id>", methods=["POST"])
def borrar_entrenamiento(id):
    modificar("DELETE FROM entrenamientos WHERE id = ?", (id,))
    return redirect(url_for("entrenamiento"))


# ------------------------------------------------------------
#  VIDA: Pasos diarios
# ------------------------------------------------------------

@app.route("/vida/pasos", methods=["GET", "POST"])
def pasos():
    if request.method == "POST":
        # "INSERT OR REPLACE": si ya había pasos ese día, se reemplazan.
        modificar("INSERT OR REPLACE INTO pasos (fecha, cantidad) VALUES (?, ?)",
                  (request.form["fecha"], int(request.form["cantidad"])))
        return redirect(url_for("pasos"))

    # Armamos los últimos 7 días, aunque alguno no tenga registro (queda en 0).
    registros = {fila["fecha"]: fila["cantidad"] for fila in consultar("SELECT * FROM pasos")}
    ultimos_7 = []
    for atras in range(6, -1, -1):
        dia = date.today() - timedelta(days=atras)
        cantidad = registros.get(dia.isoformat(), 0)
        porcentaje = min(100, round(cantidad * 100 / META_PASOS))
        ultimos_7.append({"fecha": dia.isoformat(), "nombre": DIAS_SEMANA[dia.weekday()][:3],
                          "cantidad": cantidad, "porcentaje": porcentaje})

    promedio = round(sum(d["cantidad"] for d in ultimos_7) / 7)
    return render_template("pasos.html", ultimos_7=ultimos_7, promedio=promedio,
                           meta=META_PASOS, hoy=date.today().isoformat())


# ------------------------------------------------------------
#  Arranque
# ------------------------------------------------------------

# Si pusiste contraseña pero olvidaste el secreto, mejor no arrancar:
# sin un secreto propio, alguien podría falsificar la cookie de sesión.
if CLAVE and "WEBLIFE_SECRETO" not in os.environ:
    raise RuntimeError("Falta la variable WEBLIFE_SECRETO (mira GUIA-PUBLICAR.md)")

# Creamos las tablas al cargar el archivo (también funciona en PythonAnywhere).
crear_tablas()

if __name__ == "__main__":
    # debug=True recarga la app sola cuando cambias el código. ¡Muy útil para aprender!
    app.run(debug=True)
