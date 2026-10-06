# Efectos de scroll e interacción: qué cambió

## Archivos nuevos
- **static/scroll-engine.js**: motor de scroll. Calcula el progreso (0 a 1) de cada `.scroll-section`, lo pone en `--progress` y mueve los elementos con `data-anim` (opacity, translateY, translateX, scale, blur) con la curva cubic-bezier(0.16, 1, 0.3, 1). Usa requestAnimationFrame e IntersectionObserver. También enciende palabra por palabra los titulares con `data-revelar-palabras`.
- **static/pagina-siguiente.js**: scroll continuo entre páginas. Al subir del todo arriba vuelves a la página anterior (se abre por el final y entra desde arriba). Al llegar al final de la página y seguir bajando (rueda, trackpad o dedo) se llena el círculo de "Siguiente" y se pasa a la página siguiente. Se cancela si paras 600ms o subes. No funciona con el menú o un panel abierto, ni con el cursor en un campo. Precarga la página siguiente cuando ves el footer.

## Archivos modificados
- **config_diseno.py**: `EFECTOS` (encender o apagar cada efecto), `SCROLL` (alturas 200/300/400vh, curva, opacidad inicial de las palabras), `TRANSICIONES` (450ms y 600ms), `ORDEN_PAGINAS` (Inicio → Horario → Tareas → Pendientes → Calendario → Asistencia) y `PAGINA_SIGUIENTE` (umbrales de 180px y 90px, `anterior` para encender o apagar la vuelta hacia arriba, esperas).
- **app.py**: pasa los efectos y la página siguiente a las plantillas.
- **templates/base.html**: transición entre páginas, bloque "Siguiente: …" debajo del footer y los dos archivos JS nuevos. Nuevo bloque `fuera_main` para cosas fijas en pantalla.
- **templates/calendario.html**: los avisos fijos pasan al bloque `fuera_main` (para que no se muevan con el efecto de "seguir bajando").
- **templates/inicio.html, horario.html, asistencia.html**: los titulares grandes ("Tu día", "Mis materias", "Por materia", "Últimas clases marcadas") se encienden palabra por palabra.
- **static/estilo.css**: transiciones entre páginas (el menú y el footer no se animan), bloque "Siguiente", secciones de scroll, botón que se encoge a 0.97 al pulsar, zoom 1.04 de imágenes en tarjetas, y modo "reducir movimiento" (sin animaciones, solo el enlace "Siguiente").
- **static/app.js**: el retraso escalonado de 100ms ahora vale para cualquier grupo de elementos hermanos.

## Lo que no se aplicó porque la web no tiene ese contenido
Portada con secuencia de imágenes (2), secciones de producto con revelado (3), selector "Más de cerca" (5), pestañas de experiencias (6), galería automática (7) y barra de navegación local (8). Son para páginas de producto con fotos o vídeos, y weblife es un organizador. El motor ya está listo para añadirlos.

## Recursos que tendrías que preparar si algún día quieres la portada animada
- Secuencia de imágenes: 120 fotogramas WebP, `frame_001.webp` a `frame_120.webp`, 1920×1080 para ordenador y 960×540 para móvil, de unos 40–80 KB cada uno.
- Primer y último fotograma (startframe y endframe) aparte, en WebP o JPG, al mismo tamaño.
- O en su lugar un vídeo MP4 (H.264) silencioso de 1920×1080 con un fotograma clave cada 1–2 cuadros.
