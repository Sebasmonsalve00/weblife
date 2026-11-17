"""Crea los iconos de la app (PWA) en static/iconos/.
Uso: python3 herramientas/crear_iconos.py  (necesita Pillow: pip3 install --user pillow)
Cambia COLOR_FONDO / COLOR_LETRA / LETRA y vuelve a ejecutarlo si quieres otro icono."""
import os
from PIL import Image, ImageDraw, ImageFont

COLOR_FONDO = "#A8C5FF"   # el azul pastel de la web
COLOR_LETRA = "#1D1D1F"
LETRA = "w"
FUENTE = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"   # si no existe, usa la de serie
CARPETA = os.path.join(os.path.dirname(__file__), "..", "static", "iconos")


def icono(tamano, tamano_letra, redondeado):
    escala = 4   # dibujamos grande y reducimos, para bordes suaves
    t = tamano * escala
    img = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if redondeado:
        d.rounded_rectangle((0, 0, t - 1, t - 1), radius=int(t * 0.22), fill=COLOR_FONDO)
    else:
        d.rectangle((0, 0, t, t), fill=COLOR_FONDO)
    try:
        fuente = ImageFont.truetype(FUENTE, int(t * tamano_letra))
    except OSError:
        fuente = ImageFont.load_default(int(t * tamano_letra))
    caja = d.textbbox((0, 0), LETRA, font=fuente)
    x = (t - (caja[2] - caja[0])) / 2 - caja[0]
    y = (t - (caja[3] - caja[1])) / 2 - caja[1]
    d.text((x, y), LETRA, font=fuente, fill=COLOR_LETRA)
    return img.resize((tamano, tamano), Image.LANCZOS)


os.makedirs(CARPETA, exist_ok=True)
icono(192, 0.62, True).save(os.path.join(CARPETA, "icono-192.png"))
icono(512, 0.62, True).save(os.path.join(CARPETA, "icono-512.png"))
# "maskable": Android lo recorta en círculo o gota, así que la letra va más pequeña y el fondo lleno
icono(512, 0.45, False).save(os.path.join(CARPETA, "icono-maskable-512.png"))
# iPhone: fondo lleno (iOS redondea las esquinas solo)
icono(180, 0.62, False).convert("RGB").save(os.path.join(CARPETA, "apple-touch-icon.png"))
icono(32, 0.7, True).save(os.path.join(CARPETA, "favicon-32.png"))
print("Iconos creados en", os.path.abspath(CARPETA))
