# ============================================================
#  config_diseno.py - Todo el "look" de la web en un solo lugar
#
#  Cambia aquí los colores, la fuente, los radios, el difuminado,
#  la velocidad de las animaciones o el ancho de la página.
#  app.py convierte estos valores en variables CSS (--color-fondo,
#  --radio-tarjeta, etc.) y las pone en la plantilla base, así que
#  NO hace falta tocar estilo.css para cambiarlos.
# ============================================================

# ---- 1. Paleta: solo 3 colores ----
COLORES = {
    "fondo": "#F5F5F7",    # fondo de la página
    "texto": "#1D1D1F",    # texto y botones principales
    "acento": "#A8C5FF",   # azul pastel
}

# Opacidades permitidas de esos 3 colores (variaciones, no colores nuevos).
# Nota: el texto secundario y terciario quedan en 65% y 62% (en vez de 60% y 45%)
# para cumplir el contraste mínimo WCAG AA sobre el fondo claro.
OPACIDADES = {
    "texto_secundario": 0.65,
    "texto_terciario": 0.62,
    "borde": 0.08,
    "borde_boton": 0.20,
    "superficie": 0.55,          # blanco difuminado
    "superficie_sin_blur": 0.92, # si el navegador no soporta backdrop-filter
    "acento_degradado": 0.35,
    "acento_manchas": 0.40,
    "acento_hover_fila": 0.10,
}

# ---- 2. Tipografía ----
FUENTE = {
    "nombre": "Inter",
    "respaldo": '-apple-system, "Segoe UI", sans-serif',
    # Enlace de Google Fonts con los pesos que usamos (400, 500, 600 y 700)
    "google_fonts": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
}

# ---- 3. Bordes y radios ----
RADIOS = {
    "tarjeta": "28px",   # tarjetas, paneles y tablas
    "imagen": "24px",
    "boton": "999px",    # píldora
    "input": "16px",
    "modal": "32px",     # menú móvil y sección degradada
    "chico": "12px",     # elementos pequeños (bloques del horario, días del calendario)
}

# ---- 4. Efecto difuminado (glassmorphism) ----
BLUR = {
    "superficies": "20px",   # barra de navegación, tarjetas, formularios...
    "saturacion": "180%",
    "manchas": "120px",      # manchas de color del fondo
}

# ---- Animaciones (en milisegundos) ----
ANIMACION = {
    "aparecer": 800,         # elementos .reveal al hacer scroll
    "escalonado": 100,       # retraso entre tarjetas hermanas
    "boton": 200,            # hover de botones
    "menu": 300,             # cambio de altura del menú al hacer scroll
    "menu_movil_retraso": 60,
    "flotar_manchas": 20000, # 20 segundos
}

# ---- Efectos de scroll e interacción (cada uno se puede apagar con False) ----
EFECTOS = {
    "motor_scroll": True,          # scroll-engine.js: secciones .scroll-section y atributos data-anim
    "titulares_por_palabra": True, # titulares que se encienden palabra por palabra al bajar
    "transiciones_pagina": True,   # fundido suave al cambiar de página (View Transitions)
    "pagina_siguiente": True,      # scroll continuo: la página siguiente aparece debajo al bajar
    "microinteracciones": True,    # botones que crecen/se encogen, tarjetas que suben
}

# Secciones con scroll animado (para cuando se añadan): alto de cada tipo.
SCROLL = {
    "alturas": {"corta": "200vh", "media": "300vh", "larga": "400vh"},
    "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
    # Titulares por palabra: empiezan al 15% de opacidad.
    "opacidad_inicial_palabras": 0.15,
}

# Tiempos de las transiciones entre páginas (en milisegundos).
TRANSICIONES = {
    "fundido": 700,      # la página se apaga y la nueva se aclara (en ms)
}

# Orden de páginas para el scroll continuo. Son los nombres de las rutas de app.py.
# Inicio (la bienvenida) va aparte: solo se llega con el botón "weblife".
# La última no lleva a ninguna. El nombre que se muestra sale del menú de contenido.py.
ORDEN_PAGINAS = ["horario", "tareas", "pendientes", "calendario_vista", "asistencia"]

# Fondo de burbujas: del celeste (acento) de la primera página al blanco (fondo)
# de la última. "hasta" = cuánto se acerca al blanco al final (1 sería blanco del todo).
FONDO_BURBUJAS = {
    "hasta": 0.8,        # en la última página aún queda un 20% de celeste
    "opacidad": 0.75,    # opacidad de las burbujas
}


def _mezclar(hex_a, hex_b, cuanto):
    """Color entre hex_a (cuanto=0) y hex_b (cuanto=1), en "r, g, b"."""
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return ", ".join(str(round(x + (y - x) * cuanto)) for x, y in zip(a, b))


def colores_fondo(ruta):
    """Colores de las burbujas arriba y abajo de una página, según su lugar en ORDEN_PAGINAS.
    La primera empieza en celeste y la última termina casi blanca: un degradado continuo."""
    total = len(ORDEN_PAGINAS)
    posicion = ORDEN_PAGINAS.index(ruta) if ruta in ORDEN_PAGINAS else 0
    color = lambda t: "rgba({}, {})".format(
        _mezclar(COLORES["acento"], COLORES["fondo"], t * FONDO_BURBUJAS["hasta"]), FONDO_BURBUJAS["opacidad"])
    if ruta not in ORDEN_PAGINAS:
        return {"arriba": color(0), "abajo": color(0)}
    return {"arriba": color(posicion / total), "abajo": color((posicion + 1) / total)}


PAGINA_SIGUIENTE = {
    "anterior": True,   # al subir arriba del todo, la página anterior aparece encima
    "precarga": 1.5,    # cuántas pantallas antes del final se carga la página siguiente
}

# ---- 6. Layout ----
CONTENEDOR = {
    "ancho_maximo": "1200px",
    "padding_movil": "24px",
    "padding_escritorio": "48px",
}

# Altura de la portada (hero) de la página de inicio.
# La especificación pide 100vh; si te resulta muy alta, prueba con "60vh".
HERO_ALTURA = "100vh"


def variables_css():
    """Arma el texto CSS con todas las variables para ponerlo en la plantilla base."""

    def rgba(color_hex, opacidad):
        # Convierte "#1D1D1F" + 0.08 en "rgba(29, 29, 31, 0.08)"
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        return f"rgba({r}, {g}, {b}, {opacidad})"

    texto = COLORES["texto"]
    acento = COLORES["acento"]
    o = OPACIDADES
    variables = {
        "--color-fondo": COLORES["fondo"],
        "--color-texto": texto,
        "--color-acento": acento,
        "--texto-secundario": rgba(texto, o["texto_secundario"]),
        "--texto-terciario": rgba(texto, o["texto_terciario"]),
        "--borde": rgba(texto, o["borde"]),
        "--borde-boton": rgba(texto, o["borde_boton"]),
        "--superficie": f"rgba(255, 255, 255, {o['superficie']})",
        "--superficie-sin-blur": f"rgba(255, 255, 255, {o['superficie_sin_blur']})",
        "--acento-degradado": rgba(acento, o["acento_degradado"]),
        "--acento-manchas": rgba(acento, o["acento_manchas"]),
        "--acento-suave": rgba(acento, o["acento_hover_fila"]),
        "--sombra": f"0 8px 32px {rgba(texto, 0.06)}",
        "--sombra-hover": f"0 16px 48px {rgba(texto, 0.10)}",
        "--fuente": f'"{FUENTE["nombre"]}", {FUENTE["respaldo"]}',
        "--radio-tarjeta": RADIOS["tarjeta"],
        "--radio-imagen": RADIOS["imagen"],
        "--radio-boton": RADIOS["boton"],
        "--radio-input": RADIOS["input"],
        "--radio-modal": RADIOS["modal"],
        "--radio-chico": RADIOS["chico"],
        "--blur": BLUR["superficies"],
        "--saturacion": BLUR["saturacion"],
        "--blur-manchas": BLUR["manchas"],
        "--t-aparecer": f"{ANIMACION['aparecer']}ms",
        "--t-boton": f"{ANIMACION['boton']}ms",
        "--t-menu": f"{ANIMACION['menu']}ms",
        "--t-flotar": f"{ANIMACION['flotar_manchas']}ms",
        "--ancho-contenedor": CONTENEDOR["ancho_maximo"],
        "--padding-movil": CONTENEDOR["padding_movil"],
        "--padding-escritorio": CONTENEDOR["padding_escritorio"],
        "--hero-altura": HERO_ALTURA,
        "--easing": SCROLL["easing"],
        "--t-fundido": f"{TRANSICIONES['fundido']}ms",
        "--alto-corta": SCROLL["alturas"]["corta"],
        "--alto-media": SCROLL["alturas"]["media"],
        "--alto-larga": SCROLL["alturas"]["larga"],
        "--palabra-inicial": SCROLL["opacidad_inicial_palabras"],
    }
    return "\n".join(f"  {nombre}: {valor};" for nombre, valor in variables.items())


def valores_js():
    """Los tiempos que necesita el archivo app.js (se leen desde el HTML)."""
    return {
        "escalonado": ANIMACION["escalonado"],
        "menuRetraso": ANIMACION["menu_movil_retraso"],
        "efectos": EFECTOS,
        "palabraInicial": SCROLL["opacidad_inicial_palabras"],
        "siguiente": {
            "anterior": PAGINA_SIGUIENTE["anterior"],
            "precarga": PAGINA_SIGUIENTE["precarga"],
        },
    }


def pagina_vecina(ruta_actual, menu, paso):
    """(nombre, ruta) de la página a "paso" posiciones (+1 siguiente, -1 anterior), o None."""
    if ruta_actual not in ORDEN_PAGINAS:
        return None
    posicion = ORDEN_PAGINAS.index(ruta_actual) + paso
    if not 0 <= posicion < len(ORDEN_PAGINAS):
        return None
    ruta = ORDEN_PAGINAS[posicion]
    nombres = dict((r, n) for n, r in menu)
    nombres.setdefault("inicio", "Inicio")
    return nombres.get(ruta, ruta), ruta


def pagina_siguiente(ruta_actual, menu):
    """La página que sigue a la actual (o None si es la última)."""
    return pagina_vecina(ruta_actual, menu, 1)


def pagina_anterior(ruta_actual, menu):
    """La página anterior a la actual (o None si es la primera)."""
    return pagina_vecina(ruta_actual, menu, -1)
