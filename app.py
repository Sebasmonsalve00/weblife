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
from datetime import date, datetime, timedelta

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
# Herramientas de Flask para guardar contraseñas cifradas (nunca guardamos la contraseña tal cual).
from werkzeug.security import check_password_hash, generate_password_hash

# Diseño (colores, fuente, radios...) y textos de la web, cada uno en su archivo.
import config_diseno
import contenido
import examenes
import importar_eventos

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
TABLAS_CON_DUENO = ["clases", "tareas", "eventos", "examenes_manuales"]


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

        CREATE TABLE IF NOT EXISTS examenes_ocultos (
            usuario_id INTEGER NOT NULL,
            asignatura TEXT NOT NULL,      -- examen automático que borraste del calendario
            fecha TEXT NOT NULL,
            PRIMARY KEY (usuario_id, asignatura, fecha)
        );

        CREATE TABLE IF NOT EXISTS examenes_manuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            asignatura TEXT NOT NULL,
            fecha TEXT NOT NULL,           -- "2026-12-02"
            hora TEXT,                     -- "16:00" o vacío
            carrera TEXT,
            curso TEXT,
            convocatoria TEXT
        );
    """)

    # Las cuentas creadas antes no tenían nombre y apellido: agregamos esas columnas.
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(usuarios)")]
    for columna in ("nombre_real", "apellido", "examenes_sel", "color_acento", "modo"):
        if columna not in columnas:
            conexion.execute(f"ALTER TABLE usuarios ADD COLUMN {columna} TEXT")

    # "tipo" en clases: vacío = clase de verdad, "actividad" = otra cosa que pones en el
    # horario (gimnasio, trabajo...). Las actividades no cuentan para la asistencia.
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(clases)")]
    if "tipo" not in columnas:
        conexion.execute("ALTER TABLE clases ADD COLUMN tipo TEXT")

    # Comidas de Deporte: lo que comiste cada día con sus macros (en gramos) y calorías.
    # Se llama "comidas_deporte" porque en algunas bases de datos ya existe una tabla
    # "comidas" antigua (de la sección Vida) con otras columnas.
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS comidas_deporte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,          -- "2026-10-07"
            nombre TEXT NOT NULL,         -- "Desayuno", "Batido"...
            kcal REAL NOT NULL DEFAULT 0,
            proteinas REAL NOT NULL DEFAULT 0,
            carbohidratos REAL NOT NULL DEFAULT 0,
            grasas REAL NOT NULL DEFAULT 0
        )""")
    # Más datos de cada alimento: en qué comida va (desayuno, almuerzo, cena o snack),
    # cuántos gramos, y el resto de la etiqueta (azúcares, grasas saturadas, fibra y sal)
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(comidas_deporte)")]
    for columna, tipo in (("tipo", "TEXT"), ("cantidad", "REAL"), ("azucares", "REAL"),
                          ("saturadas", "REAL"), ("fibra", "REAL"), ("sal", "REAL")):
        if columna not in columnas:
            conexion.execute(f"ALTER TABLE comidas_deporte ADD COLUMN {columna} {tipo}")

    # Datos de Deporte de cada cuenta: objetivo de calorías, reparto de macros (%)
    # y lo último que pusiste en la calculadora de IMC.
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS perfil_deporte (
            usuario_id INTEGER PRIMARY KEY,
            kcal_objetivo REAL,
            pct_proteinas REAL,
            pct_carbohidratos REAL,
            pct_grasas REAL,
            peso REAL,                    -- kg
            altura REAL                   -- cm
        )""")

    # "categoria" en clases y eventos: en Deporte, el tipo de entreno que elegiste
    # (cardio, fuerza, comida...). Ver contenido.TIPOS_DEPORTE.
    for tabla in ("clases", "eventos"):
        columnas = [fila["name"] for fila in conexion.execute(f"PRAGMA table_info({tabla})")]
        if "categoria" not in columnas:
            conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN categoria TEXT")

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

    # Eventos que añadiste de "Seleccionar evento": guardan también su tipo (examen, entrega...)
    columnas = [fila["name"] for fila in conexion.execute("PRAGMA table_info(examenes_manuales)")]
    if "tipo" not in columnas:
        conexion.execute("ALTER TABLE examenes_manuales ADD COLUMN tipo TEXT")

    # "Añade tus eventos": calendarios de eventos (exámenes, entregas...) que suben los usuarios.
    # Son de todos: cualquiera puede elegirlos en "Seleccionar evento".
    conexion.executescript("""
        CREATE TABLE IF NOT EXISTS calendarios_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            universidad TEXT NOT NULL,
            curso TEXT NOT NULL,           -- el año: "2º Curso"
            carrera TEXT NOT NULL,
            convocatoria TEXT NOT NULL,    -- "Diciembre 2026"
            subido_por INTEGER,            -- la cuenta que lo subió (vacío = de examenes.py)
            creado TEXT
        );

        CREATE TABLE IF NOT EXISTS eventos_calendario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,          -- "Corporate Communication"
            fecha TEXT NOT NULL,           -- "2026-12-02"
            hora TEXT,                     -- "16:00" o vacío
            tipo TEXT                      -- "Examen", "Entrega"...
        );

        -- Asignaturas core que el documento de la facultad trae sin fecha ("detalle en enlace").
        -- Se rellenan cuando alguien sube el documento de las core de la misma convocatoria.
        CREATE TABLE IF NOT EXISTS eventos_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendario_id INTEGER NOT NULL,   -- la carrera y año donde falta
            nombre TEXT NOT NULL,             -- "Antropología I"
            facultad TEXT                     -- "Comunicación" (para buscarla en las core de su facultad)
        );
    """)
    # Los calendarios de examenes.py se copian una vez, para elegirlos igual que los subidos.
    for carrera, cursos in examenes.CALENDARIOS.items():
        for curso, convocatorias in cursos.items():
            for convocatoria, lista in convocatorias.items():
                if conexion.execute("SELECT id FROM calendarios_eventos WHERE universidad = ? AND curso = ? "
                                    "AND carrera = ? AND convocatoria = ?",
                                    (examenes.UNIVERSIDAD, curso, carrera, convocatoria)).fetchone():
                    continue
                nuevo = conexion.execute(
                    "INSERT INTO calendarios_eventos (universidad, curso, carrera, convocatoria, creado) "
                    "VALUES (?, ?, ?, ?, ?)", (examenes.UNIVERSIDAD, curso, carrera, convocatoria, date.today().isoformat()))
                conexion.executemany(
                    "INSERT INTO eventos_calendario (calendario_id, nombre, fecha, hora, tipo) VALUES (?, ?, ?, ?, ?)",
                    [(nuevo.lastrowid, asignatura, fecha, hora, "Examen") for asignatura, fecha, hora, _ in lista])
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

def mi_acento():
    """El color que el usuario eligió en Ajustes (o None si usa el azul de siempre)."""
    if not session.get("usuario_id"):
        return None
    fila = consultar("SELECT color_acento FROM usuarios WHERE id = ?", (session["usuario_id"],))
    color = fila[0]["color_acento"] if fila else None
    return color if config_diseno.color_valido(color) else None


@app.context_processor
def datos_para_plantillas():
    acento = mi_acento()
    return {
        "variables_css": config_diseno.variables_css(acento),
        "acento": acento or config_diseno.COLORES["acento"],
        "fuente": config_diseno.FUENTE,
        "valores_js": config_diseno.valores_js(),
        "efectos": config_diseno.EFECTOS,
        "siguiente": config_diseno.pagina_siguiente(request.endpoint, contenido.menu(mi_modo())),
        "anterior": config_diseno.pagina_anterior(request.endpoint, contenido.menu(mi_modo())),
        "fondo": config_diseno.colores_fondo(request.endpoint, acento),
        "texto": contenido.todo(mi_modo()),
        "modo": mi_modo(),
    }


# ------------------------------------------------------------
#  Inicio de sesión
# ------------------------------------------------------------

def mi_cuenta():
    """El número (id) de la cuenta que inició sesión (para leer o cambiar la cuenta en sí)."""
    return session["usuario_id"]


MODOS = ("universidad", "deporte")


def mi_modo():
    """Qué calendario estás usando: "universidad" (el de siempre) o "deporte"."""
    if not session.get("usuario_id"):
        return "universidad"
    if session.get("modo") not in MODOS:
        fila = consultar("SELECT modo FROM usuarios WHERE id = ?", (mi_cuenta(),))
        session["modo"] = fila[0]["modo"] if fila and fila[0]["modo"] in MODOS else "universidad"
    return session["modo"]


def yo():
    """El dueño de los datos que ves (clases, tareas, eventos...).
    En Universidad es tu número de cuenta. En Deporte es ese número en negativo:
    así los datos de Deporte se guardan aparte y no se mezclan con los de Universidad."""
    return -mi_cuenta() if mi_modo() == "deporte" else mi_cuenta()


def es_mi_clase(id):
    """True si la clase existe y es del usuario que inició sesión."""
    return bool(consultar("SELECT id FROM clases WHERE id = ? AND usuario_id = ?", (id, yo())))


def categoria_elegida():
    """El tipo de entreno elegido en el formulario (solo en Deporte; si no, None)."""
    categoria = request.form.get("categoria")
    if mi_modo() == "deporte" and categoria in contenido.NOMBRE_TIPO_DEPORTE:
        return categoria
    return None


def con_categoria(texto, categoria):
    """Añade el tipo de entreno al texto: "Correr · Cardio"."""
    nombre = contenido.NOMBRE_TIPO_DEPORTE.get(categoria or "")
    return f"{texto} · {nombre}" if nombre and texto else (nombre or texto)


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
    """Mis datos: cambiar nombre y apellido, o cambiar la contraseña."""
    error_clave = None
    if request.method == "POST" and request.form.get("accion") == "clave":
        actual = request.form.get("clave_actual", "")
        nueva = request.form.get("clave_nueva", "")
        repetir = request.form.get("clave_repetir", "")
        fila = consultar("SELECT clave_hash FROM usuarios WHERE id = ?", (mi_cuenta(),))[0]
        if not check_password_hash(fila["clave_hash"], actual):
            error_clave = "La contraseña actual no es correcta."
        elif len(nueva) < 8:
            error_clave = "La contraseña nueva debe tener al menos 8 caracteres."
        elif nueva != repetir:
            error_clave = "Las dos contraseñas nuevas no coinciden."
        else:
            modificar("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (generate_password_hash(nueva), mi_cuenta()))
            flash(contenido.MENSAJES["clave"])
            return redirect(url_for("perfil"))
    elif request.method == "POST":
        nombre_real = request.form["nombre_real"].strip()[:40]
        apellido = request.form["apellido"].strip()[:40]
        if nombre_real and apellido:
            modificar("UPDATE usuarios SET nombre_real = ?, apellido = ? WHERE id = ?",
                      (nombre_real, apellido, yo()))
            session["nombre_real"] = nombre_real
            flash(contenido.MENSAJES["cuenta"])
            return redirect(url_for("perfil"))
    usuario = consultar("SELECT * FROM usuarios WHERE id = ?", (mi_cuenta(),))[0]
    return render_template("cuenta.html", usuario=usuario, error_clave=error_clave)


@app.route("/perfil")
def perfil():
    """Mi perfil: tus datos y dos botones (Mis datos y Mis avances)."""
    usuario = consultar("SELECT * FROM usuarios WHERE id = ?", (mi_cuenta(),))[0]
    return render_template("perfil.html", usuario=usuario)


@app.route("/perfil/modo", methods=["POST"])
def cambiar_modo():
    """Cambia de calendario: Universidad o Deporte (el interruptor del header). Cada uno tiene sus propios datos."""
    modo = request.form.get("modo")
    if modo in MODOS:
        modificar("UPDATE usuarios SET modo = ? WHERE id = ?", (modo, mi_cuenta()))
        session["modo"] = modo
        flash(contenido.MENSAJES["modo_" + modo])
    # Volvemos a la página donde estabas (solo rutas de esta web, nunca otra)
    volver = request.form.get("volver", "")
    if not volver.startswith("/") or volver.startswith("//"):
        volver = url_for("inicio")
    return redirect(volver)


@app.route("/perfil/ajustes", methods=["GET", "POST"])
def ajustes():
    """Ajustes: elegir el color que sustituye al azul en toda la web (solo para ti)."""
    if request.method == "POST":
        if request.form.get("accion") == "restablecer":
            color = None
        else:
            color = request.form.get("color_propio") if request.form.get("color") == "propio" else request.form.get("color")
            if not config_diseno.color_valido(color):
                flash(contenido.MENSAJES["color_invalido"])
                return redirect(url_for("ajustes"))
            color = color.upper()
        modificar("UPDATE usuarios SET color_acento = ? WHERE id = ?", (color, mi_cuenta()))
        flash(contenido.MENSAJES["color"])
        return redirect(url_for("ajustes"))
    return render_template("ajustes.html", colores=config_diseno.COLORES_ACENTO,
                           opacidad_burbujas=config_diseno.FONDO_BURBUJAS["opacidad"],
                           elegido=mi_acento() or config_diseno.COLORES["acento"])


@app.route("/perfil/avances")
def avances():
    """Mis avances: asistencia (de la página Asistencia) y tareas cumplidas."""
    hoy = date.today().isoformat()
    contar = lambda sql, *extra: consultar(sql, (yo(),) + extra)[0][0]
    total = contar("SELECT COUNT(*) FROM tareas WHERE usuario_id = ?")
    hechas = contar("SELECT COUNT(*) FROM tareas WHERE usuario_id = ? AND hecha = 1")
    atrasadas = contar("SELECT COUNT(*) FROM tareas WHERE usuario_id = ? AND hecha = 0 AND fecha_entrega < ?", hoy)
    # Tareas cumplidas por materia
    por_materia = consultar("""
        SELECT COALESCE(NULLIF(materia, ''), 'Sin materia') AS materia,
               SUM(hecha) AS hechas, COUNT(*) AS total
        FROM tareas WHERE usuario_id = ? GROUP BY 1 ORDER BY 1
    """, (yo(),))
    tareas = {
        "total": total, "hechas": hechas, "pendientes": total - hechas, "atrasadas": atrasadas,
        "porcentaje": round(hechas * 100 / total) if total else 0,
        "por_materia": [{"materia": f["materia"], "hechas": f["hechas"], "total": f["total"],
                         "porcentaje": round(f["hechas"] * 100 / f["total"])} for f in por_materia],
    }
    resumen = resumen_asistencia()
    resumen["actividades"] = sum(m["actividades"] for m in resumen["materias"])
    resumen["clases_fui"] = sum(m["clases_fui"] for m in resumen["materias"])
    resumen["clases_falte"] = sum(m["clases_falte"] for m in resumen["materias"])
    return render_template("avances.html", asistencia=resumen, tareas=tareas)


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


def repartir_en_carriles(bloques):
    """Si dos bloques del mismo día se pisan (misma hora), los pone uno al lado del otro.
    A cada bloque le agrega "carril" (0, 1, 2...) y "carriles" (cuántos comparten ese rato)."""
    bloques.sort(key=lambda b: (b["inicio"], b["fin"]))
    grupo, fin_grupo = [], 0
    for bloque in bloques + [None]:   # None = marca para cerrar el último grupo
        if bloque is None or (grupo and bloque["inicio"] >= fin_grupo):
            # Se terminó un grupo de bloques que se pisan: todos con el mismo número de carriles
            for b in grupo:
                b["carriles"] = max(x["carril"] for x in grupo) + 1
            grupo, fin_grupo = [], 0
        if bloque is None:
            break
        # El primer carril libre (donde el bloque anterior ya terminó)
        ocupados = {b["carril"] for b in grupo if b["fin"] > bloque["inicio"]}
        bloque["carril"] = min(c for c in range(len(grupo) + 1) if c not in ocupados)
        grupo.append(bloque)
        fin_grupo = max(fin_grupo, bloque["fin"])


@app.route("/universidad/horario", methods=["GET", "POST"])
def horario():
    error = session.pop("error_horario", None)   # si falló al editar una clase
    # Si se envió el formulario (POST), guardamos la clase nueva.
    if request.method == "POST":
        inicio = request.form["hora_inicio"]
        fin = request.form["hora_fin"]
        if a_minutos(fin) <= a_minutos(inicio):
            error = "La hora de término tiene que ser después de la hora de inicio."
        else:
            # El botón "Agregar actividad" manda tipo=actividad; "Agregar clase" no manda nada.
            tipo = "actividad" if request.form.get("tipo") == "actividad" else None
            modificar(
                "INSERT INTO clases (nombre, dia, hora_inicio, hora_fin, sala, usuario_id, tipo, categoria) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (request.form["nombre"], int(request.form["dia"]), inicio, fin, request.form["sala"], yo(), tipo,
                 categoria_elegida()),
            )
            flash(contenido.MENSAJES["actividad_extra" if tipo else "clase"])  # mensaje de éxito en el panel difuminado
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
        # Las actividades aparte no llevan asistencia ni tareas: no salen en el panel
        # (En Deporte todo sale: ahí se marca si completaste cada entreno, comida...)
        if clase["dia"] == dia_panel.weekday() and (clase["tipo"] != "actividad" or mi_modo() == "deporte"):
            pendientes_materia = consultar(
                "SELECT * FROM tareas WHERE materia = ? AND hecha = 0 AND usuario_id = ? ORDER BY fecha_entrega",
                (clase["nombre"], yo()))
            panel.append({"clase": clase, "asistio": marcas.get(clase["id"]),
                          "actividad": actividades.get(clase["id"]),
                          "pendientes": pendientes_materia})

    # ---- Texto de arriba: de qué hora a qué hora tienes clase ese día y tus horas huecas ----
    subtitulo_dia = resumen_del_dia(
        [item["clase"] for item in panel], DIAS_SEMANA[dia_panel.weekday()], dia_panel == date.today())
    if mi_modo() == "deporte":
        subtitulo_dia = [linea.replace("tienes clases", "tienes nada programado").replace("tienes clase", "tienes entreno")
                         for linea in subtitulo_dia]

    # Calculamos dónde va cada clase en la grilla:
    # "arriba" = cuántos píxeles desde las 8:00, "alto" = cuánto dura.
    limite_arriba = HORA_INICIO_DIA * 60
    limite_abajo = HORA_FIN_DIA * 60
    # En la grilla también salen las cosas del OTRO modo (Uni en Deporte y al revés),
    # solo para verlas: el panel del día y el resto de la página siguen con las del modo actual.
    # Los datos del otro modo son del mismo dueño pero con el signo cambiado (ver yo()).
    otras = consultar("SELECT * FROM clases WHERE usuario_id = ? ORDER BY dia, hora_inicio", (-yo(),))
    otro_modo = "Uni" if mi_modo() == "deporte" else "Deporte"
    por_dia = {numero: [] for numero in range(7)}
    for clase, es_otro in [(c, False) for c in clases] + [(c, True) for c in otras]:
        inicio = max(a_minutos(clase["hora_inicio"]), limite_arriba)
        fin = min(a_minutos(clase["hora_fin"]), limite_abajo)
        if fin <= inicio:
            continue  # la clase queda fuera de 8:00-20:00, no se dibuja
        por_dia[clase["dia"]].append({
            "clase": clase,
            "otro": es_otro,
            "inicio": inicio, "fin": fin,
            "arriba": (inicio - limite_arriba) * PIXELES_POR_HORA // 60,
            "alto": (fin - inicio) * PIXELES_POR_HORA // 60,
        })
    for bloques in por_dia.values():
        repartir_en_carriles(bloques)

    # Horas a la semana de cada materia (sumando todas sus clases).
    minutos_por_materia = {}
    for clase in clases:
        if clase["tipo"] == "actividad":
            continue
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
        pixeles_hora=PIXELES_POR_HORA, error=error, otro_modo=otro_modo, subtitulo_dia=subtitulo_dia,
        panel=panel, resumen=resumen, dia_panel=texto_panel, nombre_dia_panel=DIAS_SEMANA[dia_panel.weekday()],
        es_hoy=(dia_panel == date.today()),
        dia_anterior=(dia_panel - timedelta(days=1)).isoformat(),
        dia_siguiente=(dia_panel + timedelta(days=1)).isoformat(),
        entrega_sugerida=(dia_panel + timedelta(days=7)).isoformat(),
    )


@app.route("/universidad/horario/editar/<int:id>", methods=["POST"])
def editar_clase(id):
    """Cambia una clase o actividad del horario: nombre, día, horas, lugar y si es clase o actividad."""
    if not es_mi_clase(id):
        return redirect(url_for("horario"))
    inicio = request.form["hora_inicio"]
    fin = request.form["hora_fin"]
    if a_minutos(fin) <= a_minutos(inicio):
        # El horario lo enseña como error (ver horario())
        session["error_horario"] = "La hora de término tiene que ser después de la hora de inicio."
    else:
        tipo = "actividad" if request.form.get("tipo") == "actividad" else None
        modificar("UPDATE clases SET nombre = ?, dia = ?, hora_inicio = ?, hora_fin = ?, sala = ?, tipo = ?, "
                  "categoria = ? WHERE id = ? AND usuario_id = ?",
                  (request.form["nombre"], int(request.form["dia"]), inicio, fin, request.form.get("sala", ""),
                   tipo, categoria_elegida(), id, yo()))
        flash(contenido.MENSAJES["clase_editada"])
    return redirect(request.referrer or url_for("horario"))


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
    # Si la actividad era una de tus tareas pendientes, esa tarea queda como hecha
    tarea = None
    if hubo and request.form.get("tarea_id", "").isdigit():
        tarea = consultar("SELECT * FROM tareas WHERE id = ? AND usuario_id = ?",
                          (int(request.form["tarea_id"]), yo()))
    if tarea:
        modificar("UPDATE tareas SET hecha = 1 WHERE id = ? AND usuario_id = ?", (tarea[0]["id"], yo()))
        descripcion = descripcion or tarea[0]["titulo"]
    modificar("INSERT OR REPLACE INTO actividades (clase_id, fecha, hubo, descripcion) VALUES (?, ?, ?, ?)",
              (id, fecha, hubo, descripcion))
    flash(contenido.MENSAJES["actividad_tarea" if tarea else "actividad"])
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
        flash(contenido.MENSAJES["meta" if mi_modo() == "deporte" else "tarea"])
        return redirect(url_for("tareas"))

    todas = consultar("SELECT * FROM tareas WHERE usuario_id = ? ORDER BY hecha, fecha_entrega", (yo(),))
    # Las materias salen de las clases del horario (sin repetir y en orden alfabético).
    materias = [fila["nombre"] for fila in
                consultar("SELECT DISTINCT nombre FROM clases WHERE usuario_id = ? "
                          "AND (tipo IS NULL OR tipo != 'actividad') ORDER BY nombre", (yo(),))]
    # En Deporte las metas son de la semana: proponemos el domingo de esta semana.
    hoy = date.today()
    if mi_modo() == "deporte":
        hoy = hoy + timedelta(days=6 - hoy.weekday())
    return render_template("tareas.html", tareas=todas, materias=materias,
                           hoy=hoy.isoformat())


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

def avisos_calendario():
    """Arma los dos avisos del calendario:
    - examenes: los próximos exámenes (eventos que dicen "examen"), con su fecha y hora.
    - urgentes: tareas sin hacer y eventos que vencen en menos de una semana.
    "objetivo" es el momento exacto ("2026-12-07T12:00") que usa la cuenta regresiva."""
    ahora = datetime.now()
    hoy = date.today().isoformat()

    examenes_proximos = []
    urgentes = []
    for evento in consultar("SELECT * FROM eventos WHERE usuario_id = ? AND fecha >= ? ORDER BY fecha, hora",
                            (yo(), hoy)):
        # Sin hora, contamos hasta el final del día.
        objetivo = datetime.fromisoformat(f"{evento['fecha']}T{evento['hora'] or '23:59'}")
        if objetivo < ahora:
            continue  # ya pasó
        aviso = {"titulo": evento["titulo"], "fecha": evento["fecha"], "hora": evento["hora"],
                 "objetivo": objetivo.isoformat(timespec="minutes")}
        if "examen" in evento["titulo"].lower():
            examenes_proximos.append(aviso)
        elif objetivo - ahora <= timedelta(days=7):
            urgentes.append(aviso)

    en_7_dias = (date.today() + timedelta(days=7)).isoformat()
    for tarea in consultar("SELECT * FROM tareas WHERE usuario_id = ? AND hecha = 0 "
                           "AND fecha_entrega BETWEEN ? AND ?", (yo(), hoy, en_7_dias)):
        # Una tarea se entrega como tarde al final de su día.
        objetivo = datetime.fromisoformat(f"{tarea['fecha_entrega']}T23:59")
        if ahora <= objetivo and objetivo - ahora <= timedelta(days=7):
            urgentes.append({"titulo": tarea["titulo"], "fecha": tarea["fecha_entrega"], "hora": None,
                             "objetivo": objetivo.isoformat(timespec="minutes")})

    # Eventos del calendario elegido en "Seleccionar evento" (sin repetir los manuales):
    # los exámenes van a "Próximos exámenes"; lo demás (entregas...), a la semana si toca.
    manuales = examenes_manuales()
    ya_manuales = {(examen["asignatura"], examen["fecha"]) for examen in manuales}
    for asignatura, fecha, hora, tipo in examenes_elegidos()[0]:
        if (asignatura, fecha) in ya_manuales:
            continue
        objetivo = datetime.fromisoformat(f"{fecha}T{hora or '23:59'}")
        aviso = {"titulo": asignatura, "fecha": fecha, "hora": hora, "objetivo": objetivo.isoformat(timespec="minutes")}
        if objetivo < ahora:
            continue
        if importar_eventos.es_examen(tipo):
            examenes_proximos.append(aviso)
        elif objetivo - ahora <= timedelta(days=7):
            aviso["titulo"] = f"{tipo}: {asignatura}"
            urgentes.append(aviso)
    # Eventos que añadiste uno a uno en "Seleccionar evento" (o antes con "Examen manual").
    for examen in manuales:
        objetivo = datetime.fromisoformat(f"{examen['fecha']}T{examen['hora'] or '23:59'}")
        aviso = {"titulo": examen["asignatura"], "fecha": examen["fecha"], "hora": examen["hora"],
                 "objetivo": objetivo.isoformat(timespec="minutes")}
        if objetivo < ahora:
            continue
        if importar_eventos.es_examen(examen["tipo"]):
            examenes_proximos.append(aviso)
        elif objetivo - ahora <= timedelta(days=7):
            aviso["titulo"] = f"{examen['tipo']}: {examen['asignatura']}"
            urgentes.append(aviso)
    examenes_proximos.sort(key=lambda aviso: aviso["objetivo"])

    urgentes.sort(key=lambda aviso: aviso["objetivo"])
    return {"examenes": examenes_proximos[:5], "urgentes": urgentes}


@app.route("/universidad/calendario", methods=["GET", "POST"])
def calendario_vista():
    # Agregar un evento (examen, reunión, etc.)
    if request.method == "POST":
        modificar("INSERT INTO eventos (titulo, fecha, hora, usuario_id, categoria) VALUES (?, ?, ?, ?, ?)",
                  (request.form["titulo"], request.form["fecha"], request.form["hora"], yo(), categoria_elegida()))
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
        texto = con_categoria(texto, evento["categoria"])
        cosas_por_dia.setdefault(dia, []).append(
            {"texto": texto, "tipo": "evento", "id": evento["id"]})

    # Exámenes del calendario elegido (solo se ven mientras esté elegido).
    lista_examenes, eleccion = examenes_elegidos()
    manuales = examenes_manuales()
    ya_manuales = {(examen["asignatura"], examen["fecha"]) for examen in manuales}
    for asignatura, fecha, hora, tipo in sorted(lista_examenes, key=lambda e: (e[1], e[2] or "")):
        if fecha.startswith(f"{anio}-{mes:02d}-") and (asignatura, fecha) not in ya_manuales:
            texto = f"{hora} {asignatura}" if hora else asignatura
            examen = importar_eventos.es_examen(tipo)
            cosas_por_dia.setdefault(int(fecha[8:10]), []).insert(
                0, {"texto": texto if examen else f"{tipo}: {texto}", "tipo": "examen" if examen else "evento",
                    "asignatura": asignatura, "fecha": fecha, "de_calendario": True})
    # Exámenes manuales (siempre se ven, con su botón para borrarlos).
    for examen in reversed(manuales):
        if examen["fecha"].startswith(f"{anio}-{mes:02d}-"):
            texto = f"{examen['hora']} {examen['asignatura']}" if examen["hora"] else examen["asignatura"]
            es_examen = importar_eventos.es_examen(examen["tipo"])
            cosas_por_dia.setdefault(int(examen["fecha"][8:10]), []).insert(
                0, {"texto": texto if es_examen else f"{examen['tipo']}: {texto}",
                    "tipo": "examen" if es_examen else "evento", "manual_id": examen["id"]})

    # Lo del OTRO modo (Uni en Deporte y al revés) también se ve en el calendario, solo para mirarlo:
    # sin botón de borrar y con su etiqueta. Los avisos de arriba siguen siendo solo de este modo.
    otro_dueno = -yo()
    otro = "Uni" if mi_modo() == "deporte" else "Deporte"
    otros_examenes = examenes_elegidos(otro_dueno)[0]
    otros_manuales = examenes_manuales(otro_dueno)
    otros_ya_manuales = {(examen["asignatura"], examen["fecha"]) for examen in otros_manuales}
    for tarea in consultar("SELECT * FROM tareas WHERE fecha_entrega LIKE ? AND usuario_id = ?", (patron, otro_dueno)):
        cosas_por_dia.setdefault(int(tarea["fecha_entrega"][8:10]), []).append(
            {"texto": tarea["titulo"], "tipo": "tarea", "hecha": tarea["hecha"], "otro": otro})
    for evento in consultar("SELECT * FROM eventos WHERE fecha LIKE ? AND usuario_id = ? ORDER BY hora",
                            (patron, otro_dueno)):
        texto = f"{evento['hora']} {evento['titulo']}" if evento["hora"] else evento["titulo"]
        cosas_por_dia.setdefault(int(evento["fecha"][8:10]), []).append(
            {"texto": con_categoria(texto, evento["categoria"]), "tipo": "evento", "otro": otro})
    examenes_del_otro = [(e[0], e[1], e[2]) for e in otros_examenes if (e[0], e[1]) not in otros_ya_manuales]
    examenes_del_otro += [(e["asignatura"], e["fecha"], e["hora"]) for e in otros_manuales]
    for asignatura, fecha, hora in examenes_del_otro:
        if fecha.startswith(f"{anio}-{mes:02d}-"):
            texto = f"{hora} {asignatura}" if hora else asignatura
            cosas_por_dia.setdefault(int(fecha[8:10]), []).append({"texto": texto, "tipo": "examen", "otro": otro})

    # Mes anterior y siguiente para los botones ◀ ▶
    mes_anterior = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    agenda = agenda_del_mes(anio, mes, semanas, lista_examenes, manuales, ya_manuales)
    agenda_del_mes(anio, mes, semanas, otros_examenes, otros_manuales, otros_ya_manuales,
                   dueno=otro_dueno, otro=otro, agenda=agenda)
    mes_siguiente = (anio, mes + 1) if mes < 12 else (anio + 1, 1)

    return render_template(
        "calendario.html",
        semanas=semanas, anio=anio, mes=mes, nombre_mes=MESES[mes],
        dias=DIAS_SEMANA, cosas_por_dia=cosas_por_dia,
        hoy=hoy, mes_anterior=mes_anterior, mes_siguiente=mes_siguiente,
        calendarios=opciones_calendarios(), avisos=avisos_calendario(), eleccion=eleccion,
        manuales=manuales, convocatorias=examenes.CONVOCATORIAS,
        eventos_por_calendario=eventos_por_calendario(),
        mis_calendarios=consultar("SELECT * FROM calendarios_eventos WHERE subido_por = ? ORDER BY id DESC",
                                  (mi_cuenta(),)),
        ocultos=cuantos_ocultos(eleccion), agenda=agenda, texto_meses=MESES,
    )


def agenda_del_mes(anio, mes, semanas, lista_examenes, manuales, ya_manuales, dueno=None, otro=None, agenda=None):
    """Lo que tienes cada día del mes, para la vista de un día (8:00 a 20:00).
    Devuelve {dia: {"sin_hora": [...], "con_hora": [...]}}. Cada cosa con hora
    lleva "inicio" y "fin" ("09:00"); las que no tienen hora van en "sin_hora".
    Con "dueno" y "otro" ("Uni" o "Deporte") suma a "agenda" lo del otro modo, marcado con "otro"."""
    dueno = yo() if dueno is None else dueno
    agenda = {} if agenda is None else agenda

    def anotar(dia, texto, tipo, inicio=None, fin=None, detalle=""):
        del_dia = agenda.setdefault(dia, {"sin_hora": [], "con_hora": []})
        if inicio:
            # Sin hora de fin (eventos y exámenes), ocupa una hora
            if not fin:
                hora, minutos = int(inicio[:2]), inicio[3:5]
                fin = f"{min(hora + 1, 23):02d}:{minutos}"
            del_dia["con_hora"].append({"texto": texto, "tipo": tipo, "inicio": inicio[:5],
                                        "fin": fin[:5], "detalle": detalle, "otro": otro})
        else:
            del_dia["sin_hora"].append({"texto": texto, "tipo": tipo, "detalle": detalle, "otro": otro})

    prefijo = f"{anio}-{mes:02d}-"
    # Clases: se repiten cada semana el mismo día (0 = lunes)
    clases_por_dia = {}
    for clase in consultar("SELECT * FROM clases WHERE usuario_id = ? ORDER BY hora_inicio", (dueno,)):
        clases_por_dia.setdefault(clase["dia"], []).append(clase)
    for semana in semanas:
        for dia_semana, dia in enumerate(semana):
            for clase in clases_por_dia.get(dia_semana, []) if dia else []:
                anotar(dia, clase["nombre"], "actividad" if clase["tipo"] == "actividad" else "clase",
                       clase["hora_inicio"], clase["hora_fin"], con_categoria(clase["sala"] or "", clase["categoria"]))
    for tarea in consultar("SELECT * FROM tareas WHERE fecha_entrega LIKE ? AND usuario_id = ?", (prefijo + "%", dueno)):
        anotar(int(tarea["fecha_entrega"][8:10]), tarea["titulo"], "tarea-hecha" if tarea["hecha"] else "tarea",
               detalle=tarea["materia"] or "")
    for evento in consultar("SELECT * FROM eventos WHERE fecha LIKE ? AND usuario_id = ?", (prefijo + "%", dueno)):
        anotar(int(evento["fecha"][8:10]), evento["titulo"], "evento", evento["hora"],
               detalle=contenido.NOMBRE_TIPO_DEPORTE.get(evento["categoria"] or "", ""))
    for asignatura, fecha, hora, tipo in lista_examenes:
        if fecha.startswith(prefijo) and (asignatura, fecha) not in ya_manuales:
            examen = importar_eventos.es_examen(tipo)
            anotar(int(fecha[8:10]), asignatura, "examen" if examen else "evento", hora, detalle="" if examen else tipo)
    for examen in manuales:
        if examen["fecha"].startswith(prefijo):
            es_examen = importar_eventos.es_examen(examen["tipo"])
            anotar(int(examen["fecha"][8:10]), examen["asignatura"], "examen" if es_examen else "evento",
                   examen["hora"], detalle="" if es_examen else examen["tipo"])
    for del_dia in agenda.values():
        del_dia["con_hora"].sort(key=lambda cosa: cosa["inicio"])
    return agenda


def examenes_elegidos(dueno=None):
    """Los exámenes de la carrera, curso y convocatoria que eligió el usuario (o [] si no eligió).
    Devuelve (lista, (carrera, curso, convocatoria)). No se guardan como eventos:
    se leen de examenes.py cada vez, así que solo se ven mientras la opción está elegida.
    "dueno" sirve para leer los del otro modo (por defecto, yo())."""
    dueno = yo() if dueno is None else dueno
    if dueno < 0:   # los exámenes oficiales son solo de Universidad (Deporte usa el número en negativo)
        return [], None
    eleccion = calendario_elegido()
    if not eleccion:
        return [], None
    # Quitamos los que borraste con la ✕.
    ocultos = {(fila["asignatura"], fila["fecha"]) for fila in
               consultar("SELECT asignatura, fecha FROM examenes_ocultos WHERE usuario_id = ?", (dueno,))}
    lista = [(evento["nombre"], evento["fecha"], evento["hora"], evento["tipo"]) for evento in eventos_de(eleccion["id"])
             if (evento["nombre"], evento["fecha"]) not in ocultos]
    return lista, eleccion


def eventos_de(calendario_id):
    """Los eventos de un calendario de "Seleccionar evento", por fecha y hora."""
    return consultar("SELECT * FROM eventos_calendario WHERE calendario_id = ? ORDER BY fecha, hora",
                     (calendario_id,))


def calendario_elegido():
    """El calendario de eventos que elegiste en "Seleccionar evento" (o None).
    Se guarda su número en usuarios.examenes_sel."""
    fila = consultar("SELECT examenes_sel FROM usuarios WHERE id = ?", (mi_cuenta(),))
    texto = fila[0]["examenes_sel"] if fila else None
    if texto and texto.count("|") == 2:
        # Antes se guardaba "carrera|curso|convocatoria" de examenes.py: lo cambiamos por su número
        carrera, curso, convocatoria = texto.split("|")
        nuevo = consultar("SELECT id FROM calendarios_eventos WHERE universidad = ? AND carrera = ? AND curso = ? "
                          "AND convocatoria = ?", (examenes.UNIVERSIDAD, carrera, curso, convocatoria))
        texto = str(nuevo[0]["id"]) if nuevo else None
        modificar("UPDATE usuarios SET examenes_sel = ? WHERE id = ?", (texto, mi_cuenta()))
    if not texto or not texto.isdigit():
        return None
    calendario = consultar("SELECT * FROM calendarios_eventos WHERE id = ?", (int(texto),))
    return calendario[0] if calendario else None


def opciones_calendarios():
    """Todos los calendarios de eventos para "Seleccionar evento":
    {universidad: {año: {carrera: {convocatoria: número}}}}."""
    opciones = {}
    for c in consultar("SELECT * FROM calendarios_eventos ORDER BY universidad, curso, carrera, convocatoria"):
        opciones.setdefault(c["universidad"], {}).setdefault(c["curso"], {}).setdefault(
            c["carrera"], {})[c["convocatoria"]] = c["id"]
    return opciones


def eventos_por_calendario():
    """Para "Seleccionar evento": {número de calendario: [eventos]} para elegirlos uno a uno."""
    if mi_modo() == "deporte":
        return {}
    todos = {}
    for e in consultar("SELECT * FROM eventos_calendario ORDER BY fecha, hora, nombre"):
        todos.setdefault(e["calendario_id"], []).append(
            {"id": e["id"], "nombre": e["nombre"], "fecha": e["fecha"], "hora": e["hora"] or "", "tipo": e["tipo"] or ""})
    return todos


def cuantos_ocultos(eleccion):
    """Cuántos exámenes del calendario elegido borraste (para poder volver a mostrarlos)."""
    if not eleccion:
        return 0
    ocultos = {(fila["asignatura"], fila["fecha"]) for fila in
               consultar("SELECT asignatura, fecha FROM examenes_ocultos WHERE usuario_id = ?", (yo(),))}
    return sum(1 for evento in eventos_de(eleccion["id"]) if (evento["nombre"], evento["fecha"]) in ocultos)


@app.route("/universidad/calendario/examen/borrar", methods=["POST"])
def borrar_examen_automatico():
    """Esconde un examen automático: sigue en examenes.py, pero tú ya no lo ves."""
    modificar("INSERT OR IGNORE INTO examenes_ocultos (usuario_id, asignatura, fecha) VALUES (?, ?, ?)",
              (yo(), request.form["asignatura"], request.form["fecha"]))
    return redirect(request.referrer or url_for("calendario_vista"))


@app.route("/universidad/calendario/examenes", methods=["POST"])
def elegir_examenes():
    """Guarda qué calendario de exámenes quieres ver, o lo quita si pulsas "Quitar"."""
    if request.form.get("accion") == "quitar":
        modificar("UPDATE usuarios SET examenes_sel = NULL WHERE id = ?", (mi_cuenta(),))
        return redirect(url_for("calendario_vista"))
    if request.form.get("accion") == "mostrar_ocultos":
        modificar("DELETE FROM examenes_ocultos WHERE usuario_id = ?", (yo(),))
        return redirect(request.referrer or url_for("calendario_vista"))

    # "Añadir evento": los eventos marcados se copian a tu calendario (como los exámenes manuales),
    # así puedes juntar eventos de distintas carreras y años.
    ids = [int(x) for x in request.form.getlist("evento") if x.isdigit()]
    anadidos = []
    for evento_id in ids:
        fila = consultar("SELECT e.*, c.carrera, c.curso, c.convocatoria FROM eventos_calendario e "
                         "JOIN calendarios_eventos c ON c.id = e.calendario_id WHERE e.id = ?", (evento_id,))
        if not fila:
            continue
        e = fila[0]
        if not consultar("SELECT id FROM examenes_manuales WHERE usuario_id = ? AND asignatura = ? AND fecha = ?",
                         (yo(), e["nombre"], e["fecha"])):
            modificar("INSERT INTO examenes_manuales (usuario_id, asignatura, fecha, hora, carrera, curso, convocatoria, "
                      "tipo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (yo(), e["nombre"], e["fecha"], e["hora"], e["carrera"], e["curso"], e["convocatoria"], e["tipo"]))
        anadidos.append(e)
    if not anadidos:
        flash(contenido.MENSAJES["elige_evento"])
        return redirect(url_for("calendario_vista"))
    flash(contenido.MENSAJES["eventos_anadidos"].format(cuantos=len(anadidos)))
    return ir_al_primero(anadidos)


def ir_al_primero(eventos):
    """Abre el calendario en el mes del primer evento que viene (o del primero de todos si ya pasaron)."""
    fechas = sorted(evento["fecha"] for evento in eventos)
    proximas = [fecha for fecha in fechas if fecha >= date.today().isoformat()]
    primero = (proximas or fechas)[0]
    return redirect(url_for("calendario_vista", anio=int(primero[:4]), mes=int(primero[5:7])))


def calendario_de(universidad, curso, carrera, convocatoria):
    """El número del calendario de esa carrera y año (lo crea si no existe)."""
    clave = (universidad, curso, carrera, convocatoria)
    existe = consultar("SELECT id FROM calendarios_eventos WHERE universidad = ? AND curso = ? "
                       "AND carrera = ? AND convocatoria = ?", clave)
    if not existe:
        modificar("INSERT INTO calendarios_eventos (universidad, curso, carrera, convocatoria, subido_por, "
                  "creado) VALUES (?, ?, ?, ?, ?, ?)", clave + (mi_cuenta(), date.today().isoformat()))
        existe = consultar("SELECT MAX(id) AS id FROM calendarios_eventos WHERE subido_por = ?", (mi_cuenta(),))
    return existe[0]["id"]


def guardar_evento(calendario_id, nombre, fecha, hora, tipo):
    """Guarda un evento en un calendario si no estaba ya. Devuelve 1 si lo guardó, 0 si ya estaba."""
    if consultar("SELECT id FROM eventos_calendario WHERE calendario_id = ? AND nombre = ? AND fecha = ?",
                 (calendario_id, nombre, fecha)):
        return 0
    modificar("INSERT INTO eventos_calendario (calendario_id, nombre, fecha, hora, tipo) VALUES (?, ?, ?, ?, ?)",
              (calendario_id, nombre, fecha, hora, tipo))
    return 1


def rellenar_pendientes(universidad, convocatoria):
    """Pone fecha a las asignaturas core que el documento de la facultad dejó sin ella ("detalle en enlace"),
    buscándolas en los exámenes core subidos para la misma universidad y convocatoria.
    Devuelve (cuántas se rellenaron, cuántas siguen sin fecha)."""
    pendientes = consultar("SELECT p.* FROM eventos_pendientes p JOIN calendarios_eventos c ON c.id = p.calendario_id "
                           "WHERE c.universidad = ? AND c.convocatoria = ?", (universidad, convocatoria))
    core = consultar("SELECT e.*, c.carrera FROM eventos_calendario e JOIN calendarios_eventos c "
                     "ON c.id = e.calendario_id WHERE c.universidad = ? AND c.convocatoria = ? AND c.carrera LIKE ?",
                     (universidad, convocatoria, importar_eventos.CORE + " · %"))
    core = [dict(e, facultad=importar_eventos.facultad_de_core(e["carrera"])) for e in core]
    rellenadas = 0
    for pendiente in pendientes:
        calendario = consultar("SELECT carrera FROM calendarios_eventos WHERE id = ?", (pendiente["calendario_id"],))
        iguales = importar_eventos.elegir_core(pendiente["nombre"], calendario[0]["carrera"],
                                               pendiente["facultad"] or "", core)
        vistos = set()
        for examen in iguales:
            if (examen["nombre"], examen["fecha"]) not in vistos:
                vistos.add((examen["nombre"], examen["fecha"]))
                guardar_evento(pendiente["calendario_id"], examen["nombre"], examen["fecha"], examen["hora"], "Examen")
        if iguales:
            modificar("DELETE FROM eventos_pendientes WHERE id = ?", (pendiente["id"],))
            rellenadas += 1
    return rellenadas, len(pendientes) - rellenadas


@app.route("/universidad/calendario/subir-eventos", methods=["POST"])
def subir_eventos():
    """ "Añade tus eventos": lee el documento (CSV o Excel) y guarda todos sus eventos.
    Tú pones la universidad y la convocatoria; la carrera y el año de cada evento vienen en el documento,
    así que un mismo documento llena los calendarios de varias carreras y años a la vez."""
    universidad = request.form.get("universidad", "").strip()[:80]
    convocatoria = request.form.get("convocatoria", "").strip()[:80]
    archivo = request.files.get("archivo")
    if not universidad or not convocatoria or not archivo or not archivo.filename:
        flash(contenido.MENSAJES["campo_obligatorio"])
        return redirect(url_for("calendario_vista"))
    contenido_archivo = archivo.read(2 * 1024 * 1024 + 1)
    if len(contenido_archivo) > 2 * 1024 * 1024:
        flash(contenido.MENSAJES["eventos_grande"])
        return redirect(url_for("calendario_vista"))
    try:
        eventos, problemas, pendientes = importar_eventos.leer_eventos(archivo.filename, contenido_archivo,
                                                                       convocatoria)
    except Exception as error:   # documento roto o de otro tipo
        flash(str(error) if isinstance(error, ValueError) else contenido.MENSAJES["eventos_vacio"])
        return redirect(url_for("calendario_vista"))
    if not eventos and not pendientes:
        flash(contenido.MENSAJES["eventos_vacio"] + (" " + problemas[0] if problemas else ""))
        return redirect(url_for("calendario_vista"))

    # Un calendario por cada carrera y año del documento. Si ya existe (por ejemplo, lo subió
    # un compañero), le sumamos los eventos que falten.
    nuevos = 0
    calendarios = {}   # (carrera, año) -> número del calendario
    for evento in eventos + pendientes:
        grupo = (evento["carrera"], evento["curso"])
        if grupo not in calendarios:
            calendarios[grupo] = calendario_de(universidad, evento["curso"], evento["carrera"], convocatoria)
        calendario_id = calendarios[grupo]
        if "fecha" not in evento:   # asignatura core sin fecha: queda pendiente
            if not consultar("SELECT id FROM eventos_pendientes WHERE calendario_id = ? AND nombre = ?",
                             (calendario_id, evento["nombre"])):
                modificar("INSERT INTO eventos_pendientes (calendario_id, nombre, facultad) VALUES (?, ?, ?)",
                          (calendario_id, evento["nombre"], evento["facultad"]))
            continue
        nuevos += guardar_evento(calendario_id, evento["nombre"], evento["fecha"], evento["hora"], evento["tipo"])
    rellenadas, faltan = rellenar_pendientes(universidad, convocatoria)

    mensaje = contenido.MENSAJES["eventos_subidos"].format(nuevos=nuevos, calendarios=len(calendarios))
    if len(eventos) > nuevos:
        mensaje += contenido.MENSAJES["eventos_repetidos"].format(repetidos=len(eventos) - nuevos)
    if rellenadas:
        mensaje += contenido.MENSAJES["core_rellenadas"].format(cuantas=rellenadas)
    if faltan:
        mensaje += contenido.MENSAJES["core_pendientes"].format(cuantas=faltan)
    if problemas:
        mensaje += contenido.MENSAJES["eventos_problemas"].format(cuantos=len(problemas), primera=problemas[0])
    flash(mensaje)
    return redirect(url_for("calendario_vista"))


@app.route("/universidad/calendario/plantilla-eventos.csv")
def plantilla_eventos():
    """Una tabla de ejemplo para rellenar y subir en "Añade tus eventos"."""
    return Response("\ufeff" + importar_eventos.PLANTILLA, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=plantilla-eventos.csv"})


@app.route("/universidad/calendario/borrar-calendario/<int:id>", methods=["POST"])
def borrar_calendario_eventos(id):
    """Borra un calendario de eventos que subiste tú (los de otros no se pueden borrar)."""
    if consultar("SELECT id FROM calendarios_eventos WHERE id = ? AND subido_por = ?", (id, mi_cuenta())):
        modificar("DELETE FROM eventos_calendario WHERE calendario_id = ?", (id,))
        modificar("DELETE FROM eventos_pendientes WHERE calendario_id = ?", (id,))
        modificar("DELETE FROM calendarios_eventos WHERE id = ?", (id,))
        flash(contenido.MENSAJES["calendario_borrado"])
    return redirect(url_for("calendario_vista"))


def examenes_manuales(dueno=None):
    """Los exámenes que el usuario agregó con "Examen manual", ordenados por fecha."""
    return consultar("SELECT * FROM examenes_manuales WHERE usuario_id = ? ORDER BY fecha, hora",
                     (yo() if dueno is None else dueno,))


@app.route("/universidad/calendario/examen-manual/borrar/<int:id>", methods=["POST"])
def borrar_examen_manual(id):
    modificar("DELETE FROM examenes_manuales WHERE id = ? AND usuario_id = ?", (id, yo()))
    return redirect(request.referrer or url_for("calendario_vista"))


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


def numero_del_form(nombre):
    """Lee un número del formulario (vacío = 0). Nunca negativo."""
    try:
        return max(0.0, float(request.form.get(nombre, "").replace(",", ".") or 0))
    except ValueError:
        return 0.0


@app.route("/deporte/comida", methods=["POST"])
def registrar_comida():
    """Guarda un alimento en una comida del día (desayuno, almuerzo, cena o snack). Solo en Deporte."""
    fecha = request.form.get("fecha", "")
    try:
        date.fromisoformat(fecha)
    except ValueError:
        fecha = date.today().isoformat()
    tipo = request.form.get("tipo", "")
    if tipo not in dict(contenido.TIPOS_COMIDA):
        tipo = "snack"
    nombre = request.form.get("nombre", "").strip()[:60]
    if mi_modo() == "deporte" and nombre:
        cantidad = numero_del_form("cantidad")
        # Si copiaste la etiqueta "por 100 g", lo pasamos a la cantidad que comiste
        factor = cantidad / 100 if request.form.get("por_100") and cantidad else 1
        valores = {campo: round(numero_del_form(campo) * factor, 2)
                   for campo in ("kcal", "proteinas", "carbohidratos", "grasas", "azucares", "saturadas", "fibra", "sal")}
        modificar("INSERT INTO comidas_deporte (usuario_id, fecha, tipo, nombre, cantidad, kcal, proteinas, carbohidratos, "
                  "grasas, azucares, saturadas, fibra, sal) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (mi_cuenta(), fecha, tipo, nombre, cantidad or None, valores["kcal"], valores["proteinas"],
                   valores["carbohidratos"], valores["grasas"], valores["azucares"], valores["saturadas"],
                   valores["fibra"], valores["sal"]))
        flash(contenido.MENSAJES["comida"])
    return redirect(url_for("asistencia", fecha=fecha) + "#comidas")


@app.route("/deporte/comida/borrar/<int:id>", methods=["POST"])
def borrar_comida(id):
    fila = consultar("SELECT fecha FROM comidas_deporte WHERE id = ? AND usuario_id = ?", (id, mi_cuenta()))
    modificar("DELETE FROM comidas_deporte WHERE id = ? AND usuario_id = ?", (id, mi_cuenta()))
    return redirect(url_for("asistencia", fecha=fila[0]["fecha"] if fila else None) + "#comidas")


def guardar_perfil_deporte(**datos):
    """Guarda algunos datos del perfil de Deporte (crea la fila si no existe)."""
    modificar("INSERT OR IGNORE INTO perfil_deporte (usuario_id) VALUES (?)", (mi_cuenta(),))
    columnas = ", ".join(f"{columna} = ?" for columna in datos)
    modificar(f"UPDATE perfil_deporte SET {columnas} WHERE usuario_id = ?", (*datos.values(), mi_cuenta()))


@app.route("/deporte/objetivo", methods=["POST"])
def guardar_objetivo():
    """Guarda las calorías que necesitas y qué % va a proteínas, carbohidratos y grasas."""
    if mi_modo() == "deporte":
        pct = [numero_del_form("pct_proteinas"), numero_del_form("pct_carbohidratos"), numero_del_form("pct_grasas")]
        suma = sum(pct)
        if suma == 0:
            pct = [30, 40, 30]                 # reparto de ejemplo si lo dejas todo vacío
        elif round(suma) != 100:
            pct = [p * 100 / suma for p in pct]  # que siempre sume 100 %
            flash(contenido.MENSAJES["porcentajes_ajustados"])
        guardar_perfil_deporte(kcal_objetivo=numero_del_form("kcal_objetivo"), pct_proteinas=round(pct[0], 1),
                               pct_carbohidratos=round(pct[1], 1), pct_grasas=round(pct[2], 1))
        flash(contenido.MENSAJES["objetivo"])
    return redirect(url_for("asistencia", fecha=request.form.get("fecha") or None) + "#objetivo")


@app.route("/deporte/imc", methods=["POST"])
def calcular_imc():
    """Guarda tu peso y altura; la página calcula el IMC con ellos."""
    if mi_modo() == "deporte":
        altura = numero_del_form("altura")
        if 0 < altura < 3:        # si la pusiste en metros (1,75), la pasamos a centímetros
            altura *= 100
        guardar_perfil_deporte(peso=numero_del_form("peso"), altura=altura)
    return redirect(url_for("asistencia", fecha=request.form.get("fecha") or None) + "#imc")


def gramos_objetivo(perfil):
    """Gramos de cada macro: proteínas y carbohidratos tienen 4 kcal por gramo; las grasas, 9."""
    if not perfil or not perfil["kcal_objetivo"]:
        return None
    kcal = perfil["kcal_objetivo"]
    return {"kcal": round(kcal),
            "proteinas": round(kcal * (perfil["pct_proteinas"] or 0) / 100 / 4),
            "carbohidratos": round(kcal * (perfil["pct_carbohidratos"] or 0) / 100 / 4),
            "grasas": round(kcal * (perfil["pct_grasas"] or 0) / 100 / 9)}


def imc_de(perfil):
    """IMC = peso (kg) / estatura (m)². Devuelve el número y qué significa (tabla de la OMS)."""
    if not perfil or not perfil["peso"] or not perfil["altura"]:
        return None
    imc = perfil["peso"] / (perfil["altura"] / 100) ** 2
    if imc < 18.5:
        categoria = "Bajo peso"
    elif imc < 25:
        categoria = "Peso normal"
    elif imc < 30:
        categoria = "Sobrepeso"
    else:
        categoria = "Obesidad"
    return {"valor": round(imc, 1), "categoria": categoria}


def sumar_macros(comidas):
    """Total de calorías y macros de una lista de comidas (redondeado)."""
    total = {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}
    for comida in comidas:
        for clave in total:
            total[clave] += comida[clave] or 0
    return {clave: round(valor) for clave, valor in total.items()}


def alimentacion_e_info():
    """Página de Deporte: registro de comidas (macros y calorías) y resumen de la semana."""
    # Día del registro de comidas (por defecto, hoy) y semana del resumen (de lunes a domingo)
    try:
        dia = date.fromisoformat(request.args.get("fecha", ""))
    except ValueError:
        dia = date.today()
    lunes = dia - timedelta(days=dia.weekday())
    domingo = lunes + timedelta(days=6)
    dias = [lunes + timedelta(days=n) for n in range(7)]

    comidas_dia = consultar("SELECT * FROM comidas_deporte WHERE usuario_id = ? AND fecha = ? ORDER BY id",
                            (mi_cuenta(), dia.isoformat()))
    comidas_semana = consultar("SELECT * FROM comidas_deporte WHERE usuario_id = ? AND fecha BETWEEN ? AND ?",
                               (mi_cuenta(), lunes.isoformat(), domingo.isoformat()))

    # Lo programado en el horario (se repite cada semana) y lo que marcaste como completado
    clases = consultar("SELECT * FROM clases WHERE usuario_id = ? ORDER BY hora_inicio", (yo(),))
    marcas = {(fila["clase_id"], fila["fecha"]): fila["asistio"] for fila in consultar(
        "SELECT asistencias.* FROM asistencias JOIN clases ON clases.id = asistencias.clase_id "
        "WHERE clases.usuario_id = ? AND asistencias.fecha BETWEEN ? AND ?",
        (yo(), lunes.isoformat(), domingo.isoformat()))}
    eventos = consultar("SELECT * FROM eventos WHERE usuario_id = ? AND fecha BETWEEN ? AND ? ORDER BY fecha, hora",
                        (yo(), lunes.isoformat(), domingo.isoformat()))
    metas = consultar("SELECT * FROM tareas WHERE usuario_id = ? AND fecha_entrega BETWEEN ? AND ?",
                      (yo(), lunes.isoformat(), domingo.isoformat()))

    por_tipo = {}      # nombre del tipo -> {"programados", "completados"}
    filas = []         # una por día
    for fecha in dias:
        texto = fecha.isoformat()
        del_dia = [c for c in clases if c["dia"] == fecha.weekday()]
        hechos = [c for c in del_dia if marcas.get((c["id"], texto)) == 1]
        for clase in del_dia:
            tipo = contenido.NOMBRE_TIPO_DEPORTE.get(clase["categoria"] or "", "Sin tipo")
            cuenta = por_tipo.setdefault(tipo, {"programados": 0, "completados": 0})
            cuenta["programados"] += 1
            cuenta["completados"] += marcas.get((clase["id"], texto)) == 1
        filas.append({
            "fecha": fecha, "nombre": DIAS_SEMANA[fecha.weekday()], "es_hoy": fecha == date.today(),
            "programados": len(del_dia), "completados": len(hechos),
            "eventos": [con_categoria(e["titulo"], e["categoria"]) for e in eventos if e["fecha"] == texto],
            "macros": sumar_macros([c for c in comidas_semana if c["fecha"] == texto]),
        })

    programados = sum(f["programados"] for f in filas)
    completados = sum(f["completados"] for f in filas)
    dias_con_comidas = [f for f in filas if f["macros"]["kcal"] or f["macros"]["proteinas"]]
    media_kcal = round(sum(f["macros"]["kcal"] for f in dias_con_comidas) / len(dias_con_comidas)) if dias_con_comidas else 0
    # Los alimentos del día, separados por comida (los antiguos sin comida van a Snack)
    por_comida = {clave: [] for clave, nombre in contenido.TIPOS_COMIDA}
    for comida in comidas_dia:
        por_comida.get(comida["tipo"], por_comida["snack"]).append(comida)
    secciones = [{"clave": clave, "nombre": nombre, "alimentos": por_comida[clave],
                  "total": sumar_macros(por_comida[clave])} for clave, nombre in contenido.TIPOS_COMIDA]

    filas_perfil = consultar("SELECT * FROM perfil_deporte WHERE usuario_id = ?", (mi_cuenta(),))
    perfil = filas_perfil[0] if filas_perfil else None
    return render_template(
        "deporte_info.html", secciones=secciones, dia_anterior=(dia - timedelta(days=1)).isoformat(),
        dia_siguiente=(dia + timedelta(days=1)).isoformat(), perfil=perfil, objetivo=gramos_objetivo(perfil), imc=imc_de(perfil), dia=dia, hoy=date.today(), comidas=comidas_dia, total_dia=sumar_macros(comidas_dia),
        lunes=lunes, domingo=domingo, filas=filas, por_tipo=sorted(por_tipo.items()),
        programados=programados, completados=completados,
        porcentaje=round(100 * completados / programados) if programados else 0,
        metas_total=len(metas), metas_hechas=sum(1 for m in metas if m["hecha"]),
        media_kcal=media_kcal, semana_anterior=(lunes - timedelta(days=7)).isoformat(),
        semana_siguiente=(lunes + timedelta(days=7)).isoformat())


@app.route("/universidad/asistencia")
def asistencia():
    # En Deporte esta página es "Alimentación e info"
    if mi_modo() == "deporte":
        return alimentacion_e_info()
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
    # Tareas que ya completaste (las más recientes por fecha de entrega primero)
    hechas = consultar("SELECT * FROM tareas WHERE hecha = 1 AND usuario_id = ? ORDER BY fecha_entrega DESC",
                       (yo(),))
    hechas_por_materia = {}
    for tarea in hechas:
        hechas_por_materia[tarea["materia"]] = hechas_por_materia.get(tarea["materia"], 0) + 1
    return render_template("asistencia.html", resumen=resumen_asistencia(), historial=historial,
                           hechas=hechas, hechas_por_materia=hechas_por_materia)


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
