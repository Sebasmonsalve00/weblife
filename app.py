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
    """Cambia de calendario: Universidad o Deporte. Cada uno tiene sus propios datos."""
    modo = request.form.get("modo")
    if modo in MODOS:
        modificar("UPDATE usuarios SET modo = ? WHERE id = ?", (modo, mi_cuenta()))
        session["modo"] = modo
        flash(contenido.MENSAJES["modo_" + modo])
    return redirect(url_for("ajustes"))


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
                consultar("SELECT DISTINCT nombre FROM clases WHERE usuario_id = ? ORDER BY nombre", (yo(),))]
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

    # Exámenes del calendario elegido en "Fechas de examen" (sin repetir los manuales).
    manuales = examenes_manuales()
    ya_manuales = {(examen["asignatura"], examen["fecha"]) for examen in manuales}
    for asignatura, fecha, hora, _ in examenes_elegidos()[0]:
        if (asignatura, fecha) in ya_manuales:
            continue
        objetivo = datetime.fromisoformat(f"{fecha}T{hora or '23:59'}")
        if objetivo >= ahora:
            examenes_proximos.append({"titulo": asignatura, "fecha": fecha, "hora": hora,
                                      "objetivo": objetivo.isoformat(timespec="minutes")})
    # Exámenes que agregaste con "Examen manual".
    for examen in manuales:
        objetivo = datetime.fromisoformat(f"{examen['fecha']}T{examen['hora'] or '23:59'}")
        if objetivo >= ahora:
            examenes_proximos.append({"titulo": examen["asignatura"], "fecha": examen["fecha"],
                                      "hora": examen["hora"], "objetivo": objetivo.isoformat(timespec="minutes")})
    examenes_proximos.sort(key=lambda aviso: aviso["objetivo"])

    urgentes.sort(key=lambda aviso: aviso["objetivo"])
    return {"examenes": examenes_proximos[:5], "urgentes": urgentes}


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

    # Exámenes del calendario elegido (solo se ven mientras esté elegido).
    lista_examenes, eleccion = examenes_elegidos()
    manuales = examenes_manuales()
    ya_manuales = {(examen["asignatura"], examen["fecha"]) for examen in manuales}
    for asignatura, fecha, hora, _ in sorted(lista_examenes, key=lambda e: (e[1], e[2] or "")):
        if fecha.startswith(f"{anio}-{mes:02d}-") and (asignatura, fecha) not in ya_manuales:
            texto = f"{hora} {asignatura}" if hora else asignatura
            cosas_por_dia.setdefault(int(fecha[8:10]), []).insert(
                0, {"texto": texto, "tipo": "examen", "asignatura": asignatura, "fecha": fecha})
    # Exámenes manuales (siempre se ven, con su botón para borrarlos).
    for examen in reversed(manuales):
        if examen["fecha"].startswith(f"{anio}-{mes:02d}-"):
            texto = f"{examen['hora']} {examen['asignatura']}" if examen["hora"] else examen["asignatura"]
            cosas_por_dia.setdefault(int(examen["fecha"][8:10]), []).insert(
                0, {"texto": texto, "tipo": "examen", "manual_id": examen["id"]})

    # Mes anterior y siguiente para los botones ◀ ▶
    mes_anterior = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
    agenda = agenda_del_mes(anio, mes, semanas, lista_examenes, manuales, ya_manuales)
    mes_siguiente = (anio, mes + 1) if mes < 12 else (anio + 1, 1)

    return render_template(
        "calendario.html",
        semanas=semanas, anio=anio, mes=mes, nombre_mes=MESES[mes],
        dias=DIAS_SEMANA, cosas_por_dia=cosas_por_dia,
        hoy=hoy, mes_anterior=mes_anterior, mes_siguiente=mes_siguiente,
        calendarios=examenes.CALENDARIOS, avisos=avisos_calendario(), eleccion=eleccion,
        manuales=manuales, cursos=examenes.CURSOS, convocatorias=examenes.CONVOCATORIAS,
        ocultos=cuantos_ocultos(eleccion), agenda=agenda, texto_meses=MESES,
    )


def agenda_del_mes(anio, mes, semanas, lista_examenes, manuales, ya_manuales):
    """Lo que tienes cada día del mes, para la vista de un día (8:00 a 20:00).
    Devuelve {dia: {"sin_hora": [...], "con_hora": [...]}}. Cada cosa con hora
    lleva "inicio" y "fin" ("09:00"); las que no tienen hora van en "sin_hora"."""
    agenda = {}

    def anotar(dia, texto, tipo, inicio=None, fin=None, detalle=""):
        del_dia = agenda.setdefault(dia, {"sin_hora": [], "con_hora": []})
        if inicio:
            # Sin hora de fin (eventos y exámenes), ocupa una hora
            if not fin:
                hora, minutos = int(inicio[:2]), inicio[3:5]
                fin = f"{min(hora + 1, 23):02d}:{minutos}"
            del_dia["con_hora"].append({"texto": texto, "tipo": tipo, "inicio": inicio[:5],
                                        "fin": fin[:5], "detalle": detalle})
        else:
            del_dia["sin_hora"].append({"texto": texto, "tipo": tipo, "detalle": detalle})

    prefijo = f"{anio}-{mes:02d}-"
    # Clases: se repiten cada semana el mismo día (0 = lunes)
    clases_por_dia = {}
    for clase in consultar("SELECT * FROM clases WHERE usuario_id = ? ORDER BY hora_inicio", (yo(),)):
        clases_por_dia.setdefault(clase["dia"], []).append(clase)
    for semana in semanas:
        for dia_semana, dia in enumerate(semana):
            for clase in clases_por_dia.get(dia_semana, []) if dia else []:
                anotar(dia, clase["nombre"], "clase", clase["hora_inicio"], clase["hora_fin"], clase["sala"] or "")
    for tarea in consultar("SELECT * FROM tareas WHERE fecha_entrega LIKE ? AND usuario_id = ?", (prefijo + "%", yo())):
        anotar(int(tarea["fecha_entrega"][8:10]), tarea["titulo"], "tarea-hecha" if tarea["hecha"] else "tarea",
               detalle=tarea["materia"] or "")
    for evento in consultar("SELECT * FROM eventos WHERE fecha LIKE ? AND usuario_id = ?", (prefijo + "%", yo())):
        anotar(int(evento["fecha"][8:10]), evento["titulo"], "evento", evento["hora"])
    for asignatura, fecha, hora, _ in lista_examenes:
        if fecha.startswith(prefijo) and (asignatura, fecha) not in ya_manuales:
            anotar(int(fecha[8:10]), asignatura, "examen", hora)
    for examen in manuales:
        if examen["fecha"].startswith(prefijo):
            anotar(int(examen["fecha"][8:10]), examen["asignatura"], "examen", examen["hora"])
    for del_dia in agenda.values():
        del_dia["con_hora"].sort(key=lambda cosa: cosa["inicio"])
    return agenda


def examenes_elegidos():
    """Los exámenes de la carrera, curso y convocatoria que eligió el usuario (o [] si no eligió).
    Devuelve (lista, (carrera, curso, convocatoria)). No se guardan como eventos:
    se leen de examenes.py cada vez, así que solo se ven mientras la opción está elegida."""
    if mi_modo() == "deporte":   # los exámenes oficiales son solo de Universidad
        return [], None
    fila = consultar("SELECT examenes_sel FROM usuarios WHERE id = ?", (mi_cuenta(),))
    texto = fila[0]["examenes_sel"] if fila else None
    if not texto:
        return [], None
    eleccion = tuple(texto.split("|"))
    if len(eleccion) != 3:
        return [], None
    # Quitamos los que borraste con la ✕.
    ocultos = {(fila["asignatura"], fila["fecha"]) for fila in
               consultar("SELECT asignatura, fecha FROM examenes_ocultos WHERE usuario_id = ?", (yo(),))}
    lista = [examen for examen in examenes.examenes(*eleccion) if (examen[0], examen[1]) not in ocultos]
    return lista, eleccion


def cuantos_ocultos(eleccion):
    """Cuántos exámenes del calendario elegido borraste (para poder volver a mostrarlos)."""
    if not eleccion:
        return 0
    ocultos = {(fila["asignatura"], fila["fecha"]) for fila in
               consultar("SELECT asignatura, fecha FROM examenes_ocultos WHERE usuario_id = ?", (yo(),))}
    return sum(1 for examen in examenes.examenes(*eleccion) if (examen[0], examen[1]) in ocultos)


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

    eleccion = (request.form["carrera"], request.form["curso"], request.form["convocatoria"])
    lista = examenes.examenes(*eleccion)
    if not lista:
        return redirect(url_for("calendario_vista"))
    modificar("UPDATE usuarios SET examenes_sel = ? WHERE id = ?", ("|".join(eleccion), mi_cuenta()))

    # Antes los exámenes se copiaban como eventos: borramos esas copias para que no salgan dobles.
    for calendario in examenes.CALENDARIOS.values():
        for curso in calendario.values():
            for convocatoria in curso.values():
                for asignatura, fecha, _, _ in convocatoria:
                    modificar("DELETE FROM eventos WHERE titulo = ? AND fecha = ? AND usuario_id = ?",
                              (f"Examen: {asignatura}", fecha, yo()))

    # Mostramos el mes del primer examen.
    primero = min(fecha for _, fecha, _, _ in lista)
    return redirect(url_for("calendario_vista", anio=int(primero[:4]), mes=int(primero[5:7])))


def examenes_manuales():
    """Los exámenes que el usuario agregó con "Examen manual", ordenados por fecha."""
    return consultar("SELECT * FROM examenes_manuales WHERE usuario_id = ? ORDER BY fecha, hora",
                     (yo(),))


@app.route("/universidad/calendario/examen-manual", methods=["POST"])
def examen_manual():
    """Agrega un examen suelto: elegido de la lista cargada o escrito a mano."""
    carrera = request.form.get("carrera", "")
    curso = request.form.get("curso", "")
    convocatoria = request.form.get("convocatoria", "")
    if request.form.get("modo") == "lista":
        # El examen elegido viene como su número dentro de la lista de esa opción.
        lista = examenes.examenes(carrera, curso, convocatoria)
        numero = request.form.get("examen", type=int)
        if numero is None or not 0 <= numero < len(lista):
            return redirect(url_for("calendario_vista"))
        asignatura, fecha, hora, _ = lista[numero]
    else:
        asignatura = request.form.get("asignatura", "").strip()
        fecha = request.form.get("fecha", "")
        hora = request.form.get("hora") or None
        try:
            date.fromisoformat(fecha)
        except ValueError:
            fecha = ""
        if not asignatura or not fecha:
            flash(contenido.MENSAJES["campo_obligatorio"])
            return redirect(url_for("calendario_vista"))

    # Si ya lo tenías, no lo repetimos.
    if not consultar("SELECT id FROM examenes_manuales WHERE usuario_id = ? AND asignatura = ? AND fecha = ?",
                     (yo(), asignatura, fecha)):
        modificar("INSERT INTO examenes_manuales (usuario_id, asignatura, fecha, hora, carrera, curso, convocatoria) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?)", (yo(), asignatura, fecha, hora, carrera, curso, convocatoria))
    flash(contenido.MENSAJES["examen"])
    return redirect(url_for("calendario_vista", anio=int(fecha[:4]), mes=int(fecha[5:7])))


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
