# ============================================================
#  weblife - Mi página personal
#  Secciones:
#    - Universidad: horario, asistencia, tareas, calendario y pendientes
#
#  Para ejecutarla:  python app.py
#  Luego abre en el navegador:  http://127.0.0.1:5000
# ============================================================

import calendar
import hmac
import os
import re
import sqlite3
import time
from datetime import date, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
# Herramientas de Flask para guardar contraseñas cifradas (nunca guardamos la contraseña tal cual).
from werkzeug.security import check_password_hash, generate_password_hash

# Diseño (colores, fuente, radios...) y textos de la web, cada uno en su archivo.
import config_diseno
import contenido
import examenes

# Creamos la aplicación web. "__name__" le dice a Flask dónde está este archivo.
app = Flask(__name__)

# Carpeta donde está este archivo. La usamos para que la base de datos
# siempre quede al lado de app.py, la ejecutes desde donde la ejecutes.
CARPETA = os.path.dirname(os.path.abspath(__file__))

# Archivo donde se guardan todos los datos. Se crea solo la primera vez.
ARCHIVO_BD = os.path.join(CARPETA, "weblife.db")

# ------------------------------------------------------------
#  Cuentas de usuario
#  Cada persona crea su cuenta con un CÓDIGO DE INVITACIÓN que tú compartes.
#  Se leen de "variables de entorno" para no escribirlos en el código:
#  - WEBLIFE_CODIGO: el código de invitación para poder registrarse.
#    (Si no existe, se usa WEBLIFE_CLAVE, la contraseña antigua de la web.)
#  - WEBLIFE_SECRETO: un texto largo y aleatorio que Flask usa para
#    firmar la "cookie" que recuerda que ya iniciaste sesión.
#  Si no existen (en tu computador), cualquiera puede registrarse sin código.
# ------------------------------------------------------------
CODIGO = os.environ.get("WEBLIFE_CODIGO") or os.environ.get("WEBLIFE_CLAVE", "")
app.secret_key = os.environ.get("WEBLIFE_SECRETO", "solo-para-tu-computador")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"           # protege los formularios
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = bool(CODIGO)      # en internet, la cookie solo viaja por https
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)  # recordarte 30 días

# Nombres en español (Python los da en inglés por defecto).
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# ------------------------------------------------------------
#  Base de datos
# ------------------------------------------------------------

def conectar():
    """Abre una conexión con la base de datos SQLite."""
    conexion = sqlite3.connect(ARCHIVO_BD)
    # Esto permite leer las columnas por nombre: fila["titulo"]
    conexion.row_factory = sqlite3.Row
    return conexion


# Tablas que guardan datos de cada persona. (Asistencias y actividades
# cuelgan de una clase, así que su dueño es el dueño de la clase.)
TABLAS_CON_DUENO = ["clases", "tareas", "eventos"]


def crear_tablas():
    """Crea las tablas si todavía no existen."""
    conexion = conectar()
    conexion.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- "Seb" y "seb" cuentan como el mismo
            clave_hash TEXT NOT NULL,                     -- la contraseña cifrada
            creado TEXT NOT NULL
        );

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

        CREATE TABLE IF NOT EXISTS asistencias (
            clase_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,           -- el día de esa clase
            asistio INTEGER NOT NULL,      -- 1 = fui, 0 = no fui
            PRIMARY KEY (clase_id, fecha)  -- una sola marca por clase y día
        );

        CREATE TABLE IF NOT EXISTS actividades (
            clase_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,           -- el día de esa clase
            hubo INTEGER NOT NULL,         -- 1 = hubo actividad de asistencia, 0 = no hubo
            descripcion TEXT,              -- cuál fue (ej: "Quiz de derivadas")
            PRIMARY KEY (clase_id, fecha)
        );
    """)

    # Las cuentas creadas antes no tenían nombre y apellido: agregamos esas columnas.
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(usuarios)")]
    for columna in ("nombre_real", "apellido"):
        if columna not in columnas:
            conexion.execute(f"ALTER TABLE usuarios ADD COLUMN {columna} TEXT")

    # Las tablas creadas antes no tenían "fecha_creacion" en tareas: la agregamos.
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(tareas)")]
    if "fecha_creacion" not in columnas:
        conexion.execute("ALTER TABLE tareas ADD COLUMN fecha_creacion TEXT")

    # Cada clase, tarea y evento tiene dueño ("usuario_id"). Las tablas antiguas
    # no tenían esa columna: la agregamos. Los datos de antes quedan sin dueño
    # hasta que se crea la primera cuenta, que se los queda (ver registrar()).
    for tabla in TABLAS_CON_DUENO:
        columnas = [fila["name"] for fila in conexion.execute(f"PRAGMA table_info({tabla})")]
        if "usuario_id" not in columnas:
            conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN usuario_id INTEGER")
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
#  Diseño y textos para TODAS las plantillas
#  Flask llama a esta función antes de dibujar cada página, y lo que
#  devuelve queda disponible en el HTML (por ejemplo {{ texto.paginas }}).
# ------------------------------------------------------------

@app.context_processor
def datos_para_plantillas():
    return {
        "variables_css": config_diseno.variables_css(),
        "fuente": config_diseno.FUENTE,
        "valores_js": config_diseno.valores_js(),
        "texto": contenido.todo(),
    }


# ------------------------------------------------------------
#  Inicio de sesión
# ------------------------------------------------------------

def yo():
    """El número (id) del usuario que inició sesión."""
    return session["usuario_id"]


def es_mi_clase(id):
    """True si la clase existe y es del usuario que inició sesión."""
    return bool(consultar("SELECT id FROM clases WHERE id = ? AND usuario_id = ?", (id, yo())))


@app.before_request
def pedir_sesion():
    """Se ejecuta antes de cada página: si no has iniciado sesión, te manda a "Entrar"."""
    if request.endpoint in ("entrar", "registrar", "static"):
        return None
    if session.get("usuario_id"):
        # Comprobamos que la cuenta sigue existiendo (por si se borró).
        if consultar("SELECT id FROM usuarios WHERE id = ?", (session["usuario_id"],)):
            return None
        session.clear()
    return redirect(url_for("entrar"))


def iniciar_sesion(usuario):
    session.clear()
    session["usuario_id"] = usuario["id"]
    session["nombre"] = usuario["nombre"]
    session["nombre_real"] = usuario["nombre_real"] or ""   # vacío si la cuenta es de antes
    session.permanent = True


@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    error = None
    if request.method == "POST":
        filas = consultar("SELECT * FROM usuarios WHERE nombre = ?", (request.form["nombre"].strip(),))
        if filas and check_password_hash(filas[0]["clave_hash"], request.form["clave"]):
            iniciar_sesion(filas[0])
            return redirect(url_for("inicio"))
        time.sleep(1)  # frena a quien intente adivinar contraseñas muchas veces
        error = contenido.ENTRAR["error"]
    return render_template("entrar.html", error=error)


@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    error = None
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        nombre_real = request.form["nombre_real"].strip()
        apellido = request.form["apellido"].strip()
        clave = request.form["clave"]
        codigo = request.form.get("codigo", "")
        textos = contenido.REGISTRAR
        if CODIGO and not hmac.compare_digest(codigo.encode(), CODIGO.encode()):
            time.sleep(1)
            error = textos["error_codigo"]
        elif not (1 <= len(nombre_real) <= 40 and 1 <= len(apellido) <= 40):
            error = textos["error_nombre_real"]
        elif not re.fullmatch(r"[A-Za-z0-9._-]{3,30}", nombre):
            error = textos["error_nombre"]
        elif len(clave) < 8:
            error = textos["error_clave_corta"]
        elif clave != request.form["clave2"]:
            error = textos["error_claves_distintas"]
        elif consultar("SELECT id FROM usuarios WHERE nombre = ?", (nombre,)):
            error = textos["error_nombre_usado"]
        else:
            modificar("INSERT INTO usuarios (nombre, nombre_real, apellido, clave_hash, creado) "
                      "VALUES (?, ?, ?, ?, ?)",
                      (nombre, nombre_real, apellido, generate_password_hash(clave), date.today().isoformat()))
            usuario = consultar("SELECT * FROM usuarios WHERE nombre = ?", (nombre,))[0]
            # La primera cuenta se queda con los datos que había antes de las cuentas.
            if consultar("SELECT COUNT(*) AS n FROM usuarios")[0]["n"] == 1:
                for tabla in TABLAS_CON_DUENO:
                    modificar(f"UPDATE {tabla} SET usuario_id = ? WHERE usuario_id IS NULL", (usuario["id"],))
            iniciar_sesion(usuario)
            flash(textos["bienvenida"])
            return redirect(url_for("inicio"))
    return render_template("registrar.html", error=error, pide_codigo=bool(CODIGO))


@app.route("/cuenta", methods=["GET", "POST"])
def cuenta():
    """Para cambiar tu nombre y apellido (útil en cuentas creadas antes de que se pidieran)."""
    if request.method == "POST":
        nombre_real = request.form["nombre_real"].strip()[:40]
        apellido = request.form["apellido"].strip()[:40]
        if nombre_real and apellido:
            modificar("UPDATE usuarios SET nombre_real = ?, apellido = ? WHERE id = ?",
                      (nombre_real, apellido, yo()))
            session["nombre_real"] = nombre_real
            flash(contenido.MENSAJES["cuenta"])
            return redirect(url_for("inicio"))
    usuario = consultar("SELECT * FROM usuarios WHERE id = ?", (yo(),))[0]
    return render_template("cuenta.html", usuario=usuario)


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
        "SELECT * FROM clases WHERE dia = ? AND usuario_id = ? ORDER BY hora_inicio", (hoy.weekday(), yo()))
    pendientes = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND usuario_id = ? ORDER BY fecha_entrega LIMIT 5", (yo(),))
    asistencia = resumen_asistencia()

    return render_template(
        "inicio.html",
        hoy=hoy_texto,
        dia_nombre=DIAS_SEMANA[hoy.weekday()],
        clases_hoy=clases_hoy,
        pendientes=pendientes,
        asistencia=asistencia,
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


def resumen_del_dia(clases_del_dia, nombre_dia, es_hoy):
    """Devuelve dos líneas de texto, por ejemplo:
    ["Hoy lunes tienes clase de 08:00 a 13:00", "Horas huecas: 10:00–11:00"]"""
    quien = f"Hoy {nombre_dia.lower()}" if es_hoy else f"El {nombre_dia.lower()}"
    if not clases_del_dia:
        return [f"{quien} no tienes clases"]

    # Juntamos las clases que se pisan o van seguidas en un solo bloque.
    bloques = []
    for clase in sorted(clases_del_dia, key=lambda c: a_minutos(c["hora_inicio"])):
        inicio, fin = a_minutos(clase["hora_inicio"]), a_minutos(clase["hora_fin"])
        if bloques and inicio <= bloques[-1][1]:
            bloques[-1][1] = max(bloques[-1][1], fin)
        else:
            bloques.append([inicio, fin])

    def hora(minutos):
        return f"{minutos // 60:02d}:{minutos % 60:02d}"

    primera = f"{quien} tienes clase de {hora(bloques[0][0])} a {hora(bloques[-1][1])}"
    # Las horas huecas son los espacios entre un bloque y el siguiente.
    huecos = [f"{hora(a[1])}–{hora(b[0])}" for a, b in zip(bloques, bloques[1:])]
    segunda = "Horas huecas: " + (", ".join(huecos) if huecos else "ninguna")
    return [primera, segunda]


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
                "INSERT INTO clases (nombre, dia, hora_inicio, hora_fin, sala, usuario_id) VALUES (?, ?, ?, ?, ?, ?)",
                (request.form["nombre"], int(request.form["dia"]), inicio, fin, request.form["sala"], yo()),
            )
            flash(contenido.MENSAJES["clase"])  # mensaje de éxito en el panel difuminado
            return redirect(url_for("horario"))

    # Todas las clases ordenadas por día y luego por hora.
    clases = consultar("SELECT * FROM clases WHERE usuario_id = ? ORDER BY dia, hora_inicio", (yo(),))

    # ---- Panel lateral: las clases de un día (por defecto, hoy) ----
    try:
        dia_panel = date.fromisoformat(request.args.get("fecha", ""))
    except ValueError:
        dia_panel = date.today()
    texto_panel = dia_panel.isoformat()
    marcas = {fila["clase_id"]: fila["asistio"] for fila in
              consultar("SELECT asistencias.* FROM asistencias JOIN clases ON clases.id = asistencias.clase_id "
                        "WHERE asistencias.fecha = ? AND clases.usuario_id = ?", (texto_panel, yo()))}
    actividades = {fila["clase_id"]: fila for fila in
                   consultar("SELECT actividades.* FROM actividades JOIN clases ON clases.id = actividades.clase_id "
                             "WHERE actividades.fecha = ? AND clases.usuario_id = ?", (texto_panel, yo()))}
    panel = []
    for clase in clases:
        if clase["dia"] == dia_panel.weekday():
            pendientes_materia = consultar(
                "SELECT * FROM tareas WHERE materia = ? AND hecha = 0 AND usuario_id = ? ORDER BY fecha_entrega",
                (clase["nombre"], yo()))
            panel.append({"clase": clase, "asistio": marcas.get(clase["id"]),
                          "actividad": actividades.get(clase["id"]),
                          "pendientes": pendientes_materia})

    # ---- Texto de arriba: de qué hora a qué hora tienes clase ese día y tus horas huecas ----
    subtitulo_dia = resumen_del_dia(
        [item["clase"] for item in panel], DIAS_SEMANA[dia_panel.weekday()], dia_panel == date.today())

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

    # Horas a la semana de cada materia (sumando todas sus clases).
    minutos_por_materia = {}
    for clase in clases:
        duracion = a_minutos(clase["hora_fin"]) - a_minutos(clase["hora_inicio"])
        minutos_por_materia[clase["nombre"]] = minutos_por_materia.get(clase["nombre"], 0) + duracion
    resumen = []
    for nombre in sorted(minutos_por_materia):
        horas, minutos = divmod(minutos_por_materia[nombre], 60)
        texto = f"{horas} h" + (f" {minutos} min" if minutos else "")
        resumen.append({"nombre": nombre, "texto": texto})

    # De lunes a viernes siempre; sábado y domingo solo si tienen clases.
    dias_visibles = [d for d in range(7) if d < 5 or por_dia[d]]
    horas = [f"{h:02d}:00" for h in range(HORA_INICIO_DIA, HORA_FIN_DIA + 1)]

    return render_template(
        "horario.html", dias=DIAS_SEMANA, dias_visibles=dias_visibles, por_dia=por_dia,
        clases=clases, horas=horas, alto_total=(HORA_FIN_DIA - HORA_INICIO_DIA) * PIXELES_POR_HORA,
        pixeles_hora=PIXELES_POR_HORA, error=error, subtitulo_dia=subtitulo_dia,
        panel=panel, resumen=resumen, dia_panel=texto_panel, nombre_dia_panel=DIAS_SEMANA[dia_panel.weekday()],
        es_hoy=(dia_panel == date.today()),
        dia_anterior=(dia_panel - timedelta(days=1)).isoformat(),
        dia_siguiente=(dia_panel + timedelta(days=1)).isoformat(),
        entrega_sugerida=(dia_panel + timedelta(days=7)).isoformat(),
    )


@app.route("/universidad/horario/borrar/<int:id>", methods=["POST"])
def borrar_clase(id):
    if not es_mi_clase(id):
        return redirect(url_for("horario"))
    modificar("DELETE FROM clases WHERE id = ?", (id,))
    modificar("DELETE FROM asistencias WHERE clase_id = ?", (id,))
    modificar("DELETE FROM actividades WHERE clase_id = ?", (id,))
    return redirect(url_for("horario"))


@app.route("/universidad/horario/asistencia/<int:id>", methods=["POST"])
def marcar_asistencia(id):
    """Guarda si fuiste (1) o no (0) a una clase en un día. Si vuelves a apretar el mismo botón, se borra."""
    fecha = request.form["fecha"]
    if not es_mi_clase(id):
        return redirect(url_for("horario", fecha=fecha))
    asistio = int(request.form["asistio"])
    anterior = consultar("SELECT asistio FROM asistencias WHERE clase_id = ? AND fecha = ?", (id, fecha))
    if anterior and anterior[0]["asistio"] == asistio:
        modificar("DELETE FROM asistencias WHERE clase_id = ? AND fecha = ?", (id, fecha))
    else:
        modificar("INSERT OR REPLACE INTO asistencias (clase_id, fecha, asistio) VALUES (?, ?, ?)",
                  (id, fecha, asistio))
    return redirect(url_for("horario", fecha=fecha))


@app.route("/universidad/horario/actividad/<int:id>", methods=["POST"])
def guardar_actividad(id):
    """Guarda si en esa clase hubo una actividad de asistencia (quiz, lista, taller...) y cuál fue."""
    fecha = request.form["fecha"]
    if not es_mi_clase(id):
        return redirect(url_for("horario", fecha=fecha))
    hubo = int(request.form["hubo"])
    descripcion = request.form.get("descripcion", "").strip() if hubo else ""
    modificar("INSERT OR REPLACE INTO actividades (clase_id, fecha, hubo, descripcion) VALUES (?, ?, ?, ?)",
              (id, fecha, hubo, descripcion))
    flash(contenido.MENSAJES["actividad"])
    return redirect(url_for("horario", fecha=fecha))


@app.route("/universidad/horario/tarea/<int:id>", methods=["POST"])
def tarea_rapida(id):
    """Agrega una tarea desde el panel del horario, con la materia de esa clase."""
    clase = consultar("SELECT nombre FROM clases WHERE id = ? AND usuario_id = ?", (id, yo()))
    if clase:
        guardar_tarea(request.form["titulo"], clase[0]["nombre"], request.form["fecha_entrega"])
        flash(contenido.MENSAJES["tarea"])
    return redirect(url_for("horario", fecha=request.form["fecha"]))


# ------------------------------------------------------------
#  UNIVERSIDAD: Tareas
# ------------------------------------------------------------

def guardar_tarea(titulo, materia, fecha_entrega):
    """Guarda una tarea nueva con la fecha de hoy como fecha de creación."""
    modificar(
        "INSERT INTO tareas (titulo, materia, fecha_entrega, fecha_creacion, usuario_id) VALUES (?, ?, ?, ?, ?)",
        (titulo, materia, fecha_entrega, date.today().isoformat(), yo()),
    )


@app.route("/universidad/tareas", methods=["GET", "POST"])
def tareas():
    if request.method == "POST":
        guardar_tarea(request.form["titulo"], request.form["materia"], request.form["fecha_entrega"])
        flash(contenido.MENSAJES["tarea"])
        return redirect(url_for("tareas"))

    todas = consultar("SELECT * FROM tareas WHERE usuario_id = ? ORDER BY hecha, fecha_entrega", (yo(),))
    # Las materias salen de las clases del horario (sin repetir y en orden alfabético).
    materias = [fila["nombre"] for fila in
                consultar("SELECT DISTINCT nombre FROM clases WHERE usuario_id = ? ORDER BY nombre", (yo(),))]
    return render_template("tareas.html", tareas=todas, materias=materias,
                           hoy=date.today().isoformat())


@app.route("/universidad/tareas/cambiar/<int:id>", methods=["POST"])
def cambiar_tarea(id):
    # "1 - hecha" cambia 0 por 1 y 1 por 0 (marcar / desmarcar).
    modificar("UPDATE tareas SET hecha = 1 - hecha WHERE id = ? AND usuario_id = ?", (id, yo()))
    # Volvemos a la página desde donde se hizo clic.
    return redirect(request.referrer or url_for("tareas"))


@app.route("/universidad/tareas/borrar/<int:id>", methods=["POST"])
def borrar_tarea(id):
    modificar("DELETE FROM tareas WHERE id = ? AND usuario_id = ?", (id, yo()))
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
        "SELECT * FROM tareas WHERE hecha = 0 AND usuario_id = ? AND fecha_entrega < ? ORDER BY fecha_entrega",
        (yo(), hoy))
    esta_semana = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND usuario_id = ? AND fecha_entrega BETWEEN ? AND ? ORDER BY fecha_entrega",
        (yo(), hoy, en_7_dias))
    despues = consultar(
        "SELECT * FROM tareas WHERE hecha = 0 AND usuario_id = ? AND fecha_entrega > ? ORDER BY fecha_entrega",
        (yo(), en_7_dias))

    return render_template("pendientes.html", atrasadas=atrasadas,
                           esta_semana=esta_semana, despues=despues)


# ------------------------------------------------------------
#  UNIVERSIDAD: Calendario mensual
# ------------------------------------------------------------

@app.route("/universidad/calendario", methods=["GET", "POST"])
def calendario_vista():
    # Agregar un evento (examen, reunión, etc.)
    if request.method == "POST":
        modificar("INSERT INTO eventos (titulo, fecha, hora, usuario_id) VALUES (?, ?, ?, ?)",
                  (request.form["titulo"], request.form["fecha"], request.form["hora"], yo()))
        fecha = date.fromisoformat(request.form["fecha"])
        flash(contenido.MENSAJES["evento"])
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
    for tarea in consultar("SELECT * FROM tareas WHERE fecha_entrega LIKE ? AND usuario_id = ?", (patron, yo())):
        dia = int(tarea["fecha_entrega"][8:10])
        cosas_por_dia.setdefault(dia, []).append(
            {"texto": tarea["titulo"], "tipo": "tarea", "hecha": tarea["hecha"]})
    for evento in consultar("SELECT * FROM eventos WHERE fecha LIKE ? AND usuario_id = ? ORDER BY hora",
                            (patron, yo())):
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
        calendarios=examenes.CALENDARIOS,
    )


@app.route("/universidad/calendario/examenes", methods=["POST"])
def cargar_examenes():
    """Agrega al calendario todas las fechas de examen de la carrera, curso y convocatoria elegidos."""
    lista = examenes.examenes(request.form["carrera"], request.form["curso"], request.form["convocatoria"])
    agregados = 0
    for asignatura, fecha, hora, _ in lista:
        titulo = f"Examen: {asignatura}"
        # Si ya estaba (por cargarlo dos veces), no lo repetimos.
        if not consultar("SELECT id FROM eventos WHERE titulo = ? AND fecha = ? AND usuario_id = ?",
                         (titulo, fecha, yo())):
            modificar("INSERT INTO eventos (titulo, fecha, hora, usuario_id) VALUES (?, ?, ?, ?)",
                      (titulo, fecha, hora, yo()))
            agregados += 1
    if not lista:
        return redirect(url_for("calendario_vista"))
    flash(contenido.MENSAJES["examenes"].format(agregados))
    # Mostramos el mes del primer examen.
    primero = min(fecha for _, fecha, _, _ in lista)
    return redirect(url_for("calendario_vista", anio=int(primero[:4]), mes=int(primero[5:7])))


@app.route("/universidad/calendario/borrar/<int:id>", methods=["POST"])
def borrar_evento(id):
    modificar("DELETE FROM eventos WHERE id = ? AND usuario_id = ?", (id, yo()))
    return redirect(request.referrer or url_for("calendario_vista"))


# ------------------------------------------------------------
#  UNIVERSIDAD: Asistencia (horas que fuiste a cada materia)
# ------------------------------------------------------------

def texto_horas(minutos):
    """Convierte 90 en "1 h 30 min" y 120 en "2 h"."""
    horas, resto = divmod(minutos, 60)
    if horas and resto:
        return f"{horas} h {resto} min"
    if horas:
        return f"{horas} h"
    return f"{resto} min"


def resumen_asistencia():
    """Suma, por materia, los minutos de las clases a las que fuiste y a las que no.
    Usa las marcas "Fui" / "No fui" del panel del horario."""
    marcas = consultar("""
        SELECT clases.nombre, clases.hora_inicio, clases.hora_fin, asistencias.asistio
        FROM asistencias JOIN clases ON clases.id = asistencias.clase_id
        WHERE clases.usuario_id = ?
    """, (yo(),))
    # Actividades de asistencia (solo las que sí hubo), contadas por materia.
    actividades_por_materia = {}
    for fila in consultar("""
        SELECT clases.nombre FROM actividades JOIN clases ON clases.id = actividades.clase_id
        WHERE actividades.hubo = 1 AND clases.usuario_id = ?
    """, (yo(),)):
        actividades_por_materia[fila["nombre"]] = actividades_por_materia.get(fila["nombre"], 0) + 1

    materias = {}
    for marca in marcas:
        duracion = a_minutos(marca["hora_fin"]) - a_minutos(marca["hora_inicio"])
        datos = materias.setdefault(marca["nombre"], {"fui": 0, "falte": 0, "clases_fui": 0, "clases_falte": 0})
        if marca["asistio"]:
            datos["fui"] += duracion
            datos["clases_fui"] += 1
        else:
            datos["falte"] += duracion
            datos["clases_falte"] += 1

    filas = []
    for nombre in sorted(materias):
        datos = materias[nombre]
        total = datos["fui"] + datos["falte"]
        filas.append({
            "nombre": nombre,
            "horas_fui": texto_horas(datos["fui"]),
            "horas_falte": texto_horas(datos["falte"]),
            "clases_fui": datos["clases_fui"],
            "clases_falte": datos["clases_falte"],
            "porcentaje": round(datos["fui"] * 100 / total) if total else 0,
            "actividades": actividades_por_materia.get(nombre, 0),
        })
    minutos_fui = sum(d["fui"] for d in materias.values())
    minutos_total = minutos_fui + sum(d["falte"] for d in materias.values())
    return {
        "materias": filas,
        "total_fui": texto_horas(minutos_fui),
        "porcentaje": round(minutos_fui * 100 / minutos_total) if minutos_total else 0,
        "hay_datos": minutos_total > 0,
    }


@app.route("/universidad/asistencia")
def asistencia():
    # Últimas 30 marcas, para ver el detalle día a día.
    historial = consultar("""
        SELECT asistencias.fecha, asistencias.asistio, clases.nombre, clases.hora_inicio, clases.hora_fin,
               actividades.hubo, actividades.descripcion
        FROM asistencias JOIN clases ON clases.id = asistencias.clase_id
        LEFT JOIN actividades ON actividades.clase_id = asistencias.clase_id
                             AND actividades.fecha = asistencias.fecha
        WHERE clases.usuario_id = ?
        ORDER BY asistencias.fecha DESC, clases.hora_inicio DESC LIMIT 30
    """, (yo(),))
    return render_template("asistencia.html", resumen=resumen_asistencia(), historial=historial)


# ------------------------------------------------------------
#  Arranque
# ------------------------------------------------------------

# Si pusiste contraseña pero olvidaste el secreto, mejor no arrancar:
# sin un secreto propio, alguien podría falsificar la cookie de sesión.
if CODIGO and "WEBLIFE_SECRETO" not in os.environ:
    raise RuntimeError("Falta la variable WEBLIFE_SECRETO (mira GUIA-PUBLICAR.md)")

# Creamos las tablas al cargar el archivo (también funciona en PythonAnywhere).
crear_tablas()

if __name__ == "__main__":
    # debug=True recarga la app sola cuando cambias el código. ¡Muy útil para aprender!
    app.run(debug=True)
