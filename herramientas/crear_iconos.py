"""Crea los iconos de la app (PWA) en static/iconos/.
Uso: python3 herramientas/crear_iconos.py  (necesita Pillow: pip3 install --user pillow)

Hay tres diseños; cambia DISENO y vuelve a ejecutarlo:
  "A": estilo Apple: fondo claro con manchas del azul de la web y una "w" en Inter Bold
       (la misma letra que el logo de la web).
  "B": tarjeta de cristal sobre un degradado pastel.
  "C": fondo oscuro con la "w" en degradado pastel y un punto.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DISENO = "A"
CARPETA = os.path.join(os.path.dirname(__file__), "..", "static", "iconos")

# Inter, la letra de la web. Si no está en tu ordenador, descárgala de Google Fonts y pon aquí la ruta.
FUENTE_INTER = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"

S = 1024   # dibujamos grande y luego reducimos, para que los bordes queden suaves
FONDO = (245, 245, 247)     # #F5F5F7, el fondo de la web
TEXTO = (29, 29, 31)        # #1D1D1F
AZUL = (168, 197, 255)      # #A8C5FF, el acento
LILA = (209, 184, 255)
CELESTE = (168, 224, 255)
ROSA = (255, 184, 209)


def manchas(base, lista):
    """Fondo con manchas de color difuminadas, como las de detrás de la web."""
    capa = Image.new("RGB", (S, S), base)
    for cx, cy, r, color, fuerza in lista:
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=int(255 * fuerza))
        m = m.filter(ImageFilter.GaussianBlur(r * 0.45))
        capa = Image.composite(Image.new("RGB", (S, S), color), capa, m)
    return capa


def w_trazo(d, color, grosor, y0=330, y1=700, x0=250, x1=774, ymedio=430):
    """La "w" como una sola línea con las puntas redondeadas."""
    xs = [x0, x0 + (x1 - x0) * 0.25, (x0 + x1) / 2, x0 + (x1 - x0) * 0.75, x1]
    puntos = [(xs[0], y0), (xs[1], y1), (xs[2], ymedio), (xs[3], y1), (xs[4], y0)]
    d.line(puntos, fill=color, width=grosor, joint="curve")
    for x, y in puntos:
        d.ellipse((x - grosor / 2, y - grosor / 2, x + grosor / 2, y + grosor / 2), fill=color)


def diseno_a():
    # Fondo casi blanco que baja suave al gris de la web, como los iconos de Apple
    img = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / S
        d.line((0, y, S, y), fill=tuple(int(255 + (f - 255) * t) for f in FONDO))
    # Manchas de un solo color: el azul por defecto (#A8C5FF)
    img = manchas_sobre(img, [(170, 180, 430, 0.95), (900, 880, 420, 0.75)], AZUL)
    # La "w" en Inter Bold, con el mismo espaciado apretado que el logo
    fuente = ImageFont.truetype(FUENTE_INTER, int(S * 0.56))
    caja = d.textbbox((0, 0), "w", font=fuente)
    x = (S - (caja[2] - caja[0])) / 2 - caja[0]
    y = (S - (caja[3] - caja[1])) / 2 - caja[1]
    ImageDraw.Draw(img).text((x, y), "w", font=fuente, fill=TEXTO)
    return img


def manchas_sobre(img, lista, color):
    for cx, cy, r, fuerza in lista:
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=int(255 * fuerza))
        m = m.filter(ImageFilter.GaussianBlur(r * 0.5))
        img = Image.composite(Image.new("RGB", (S, S), color), img, m)
    return img


def diseno_b():
    img = manchas(AZUL, [(150, 150, 500, CELESTE, 1), (950, 950, 520, LILA, 1), (900, 200, 300, ROSA, 0.5)])
    cristal = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(cristal).rounded_rectangle((170, 170, 854, 854), radius=170, fill=(255, 255, 255, 120),
                                              outline=(255, 255, 255, 200), width=8)
    img = Image.alpha_composite(img.convert("RGBA"), cristal).convert("RGB")
    w_trazo(ImageDraw.Draw(img), TEXTO, 80, y0=380, y1=650, x0=300, x1=724, ymedio=460)
    return img


def diseno_c():
    img = Image.new("RGB", (S, S), TEXTO)
    mascara = Image.new("L", (S, S), 0)
    w_trazo(ImageDraw.Draw(mascara), 255, 104)
    img.paste(manchas(AZUL, [(250, 300, 380, CELESTE, 1), (800, 750, 380, LILA, 1)]), (0, 0), mascara)
    ImageDraw.Draw(img).ellipse((S / 2 - 34, 196, S / 2 + 34, 264), fill=AZUL)
    return img


def guardar(img, nombre, tamano, redondeado):
    if redondeado:   # esquinas redondeadas (Android y pestañas); iPhone las redondea solo
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * 0.225), fill=255)
        con_esquinas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        con_esquinas.paste(img, (0, 0), m)
        img = con_esquinas
    img.resize((tamano, tamano), Image.LANCZOS).save(os.path.join(CARPETA, nombre))


os.makedirs(CARPETA, exist_ok=True)
icono = {"A": diseno_a, "B": diseno_b, "C": diseno_c}[DISENO]()
guardar(icono, "icono-192.png", 192, True)
guardar(icono, "icono-512.png", 512, True)
guardar(icono, "icono-maskable-512.png", 512, False)   # Android lo recorta él (la "w" cabe en la zona segura)
guardar(icono, "apple-touch-icon.png", 180, False)
guardar(icono, "favicon-32.png", 32, True)
print("Iconos (diseño", DISENO + ") creados en", os.path.abspath(CARPETA))
