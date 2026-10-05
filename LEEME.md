# weblife: mi página personal

Una web hecha con **Python + Flask** y una base de datos **SQLite**, con dos secciones:

- 🎓 **Universidad**: horario semanal de clases, tareas, calendario mensual (tareas + eventos como exámenes) y lista de pendientes (atrasadas, esta semana, más adelante).
- 🌱 **Vida**: alimentación (comidas y calorías), entrenamiento (tipo, minutos, notas) y pasos diarios con gráfico de la semana.

Todo se guarda en el archivo `weblife.db`, que se crea solo la primera vez.

## Cómo ejecutarla en tu computador

1. Instala Python 3 desde python.org (en Windows marca la casilla **"Add Python to PATH"**).
2. Descarga la carpeta `weblife` y ábrela en una terminal (en VS Code: *Terminal → New Terminal*).
3. Crea un entorno virtual e instala Flask:

   **Windows**
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   **Mac / Linux**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Ejecuta la app:
   ```
   python app.py
   ```
5. Abre en el navegador: **http://127.0.0.1:5000**

Para detenerla, presiona `Ctrl + C` en la terminal. La próxima vez solo repites el paso de activar el entorno (`activate`) y `python app.py`.

## Usarla desde internet

Para tenerla en internet con contraseña (y abrirla desde el celular), sigue [GUIA-PUBLICAR.md](GUIA-PUBLICAR.md).

## Cómo está organizada

```
weblife/
├── app.py              ← todo el código Python (rutas y base de datos)
├── requirements.txt    ← librerías necesarias (solo Flask)
├── templates/          ← las páginas HTML
│   ├── base.html       ← el menú y el "esqueleto" que comparten todas
│   ├── inicio.html     ← resumen del día
│   ├── horario.html, tareas.html, pendientes.html, calendario.html
│   └── alimentacion.html, entrenamiento.html, pasos.html
└── static/
    └── estilo.css      ← colores y diseño
```

**Cómo funciona una página**, por ejemplo `/vida/pasos`:

1. En `app.py`, `@app.route("/vida/pasos")` le dice a Flask qué función responde a esa dirección.
2. La función lee la base de datos con `consultar(...)` (o guarda con `modificar(...)` si enviaste el formulario).
3. Termina con `render_template("pasos.html", ...)`, que rellena el HTML con esos datos.
4. En el HTML, `{{ variable }}` muestra un valor y `{% for ... %}` repite algo por cada elemento.

## Ideas para seguir aprendiendo

- Cambia `META_PASOS` en `app.py` o los colores al inicio de `static/estilo.css`.
- Agrega un campo nuevo, por ejemplo "peso corporal" en la sección Vida (nueva tabla en `crear_tablas`, nueva ruta y nueva plantilla, copiando el patrón de `pasos`).
- Agrega un botón para editar una tarea, no solo borrarla.
