# Publicar weblife en internet (PythonAnywhere, gratis)

Al terminar, tu web quedará en **https://TU-USUARIO.pythonanywhere.com**, protegida con contraseña, y la podrás abrir desde el celular o cualquier computador. No se instala nada en tu Mac.

## 1. Crea tu cuenta

1. Entra a **https://www.pythonanywhere.com** y haz clic en **Pricing & signup**.
2. Elige **Create a Beginner account** (es la gratis).
3. El nombre de usuario que elijas será parte de la dirección de tu web: `usuario.pythonanywhere.com`.

## 2. Sube los archivos

1. Arriba a la derecha, entra a **Files**.
2. Haz clic en **Upload a file** y sube `weblife.zip`.
3. Entra a **Consoles** y haz clic en **Bash**. Se abre una terminal en el navegador.
4. Escribe esto y presiona Enter:
   ```
   unzip weblife.zip
   ```
5. En esa misma consola, genera tu "secreto" (un texto largo y aleatorio):
   ```
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copia el texto que aparece. Lo usarás en el paso 4.

## 3. Crea la web

1. Entra a la pestaña **Web** y haz clic en **Add a new web app** → **Next**.
2. Elige **Manual configuration** (¡no "Flask"!) y luego la versión de Python más nueva que aparezca → **Next**.
3. En la página que aparece, busca la sección **Code**:
   - En **Source code** escribe: `/home/TU-USUARIO/weblife`
   - En **Working directory** escribe lo mismo.

## 4. Conecta tu código y pon tu código de invitación

1. En esa misma sección **Code**, haz clic en el enlace del **WSGI configuration file** (termina en `_wsgi.py`).
2. **Borra todo** lo que tiene el archivo y pega esto (cada línea debe quedar pegada al borde izquierdo, sin espacios al inicio):

```python
import os
import sys
import time

# Código de invitación: solo quien lo tenga puede crear una cuenta en tu web.
# Compártelo solo con las personas que quieras invitar.
os.environ["WEBLIFE_CODIGO"] = "escribe-aqui-tu-codigo"

# El texto largo que generaste en el paso 2
os.environ["WEBLIFE_SECRETO"] = "pega-aqui-el-secreto"

# Correo para "¿Has olvidado tu contraseña?" (opcional, ver "Recuperar contraseña" abajo)
os.environ["WEBLIFE_CORREO"] = "tu-cuenta@gmail.com"
os.environ["WEBLIFE_CORREO_CLAVE"] = "pega-aqui-la-contrasena-de-aplicacion"
# Opcional: para leer fotos con Claude (ver "Leer fotos" más abajo)
# os.environ["WEBLIFE_CLAUDE_CLAVE"] = "pega-aqui-tu-clave-de-claude"

# Tu zona horaria, para que "hoy" sea tu día y no el del servidor.
# Ejemplos: America/Santiago, America/Bogota, America/Mexico_City, Europe/Madrid
os.environ["TZ"] = "Europe/Madrid"
time.tzset()

sys.path.insert(0, "/home/TU-USUARIO/weblife")
from app import app as application
```

3. Cambia `TU-USUARIO`, el código, el secreto y la zona horaria. Luego haz clic en **Save**.

## 5. Actívala

1. Vuelve a la pestaña **Web**.
2. En la sección **Security**, activa **Force HTTPS**.
3. Arriba, haz clic en el botón verde **Reload**.
4. Abre `https://TU-USUARIO.pythonanywhere.com`, pulsa **Crear una cuenta** y usa tu código. 🎉

## Recuperar contraseña por correo

La web manda el enlace de "¿Has olvidado tu contraseña?" desde una cuenta de Gmail.
La cuenta gratis de PythonAnywhere solo permite enviar correo por Gmail (smtp.gmail.com, puerto 587).

1. En esa cuenta de Gmail activa la **verificación en dos pasos** (myaccount.google.com → Seguridad).
2. Entra en **myaccount.google.com/apppasswords**, crea una contraseña de aplicación llamada `weblife`
   y copia las 16 letras que te da Google.
3. Pon el correo y esas 16 letras en `WEBLIFE_CORREO` y `WEBLIFE_CORREO_CLAVE` del archivo WSGI, **Save** y **Reload**.

Nunca escribas esa contraseña en el código ni en GitHub: solo en el archivo WSGI.
Las cuentas creadas antes no tienen correo: cada persona lo añade en **Mi perfil → Mis datos**.

## Leer fotos (PNG/JPG) con Claude (opcional)

Las subidas de horario, entrenos y eventos aceptan fotos o capturas. Sin hacer nada, la foto se lee
en el navegador (gratis, pero solo entiende bien capturas claras). Con una clave de Claude la lee
el servidor y entiende casi cualquier imagen (horarios, listas de exámenes, planes de entreno...).
PythonAnywhere gratis sí deja hablar con `api.anthropic.com`.

1. Entra en **console.anthropic.com**, crea una cuenta, añade un poco de saldo (cada foto cuesta
   menos de 1 céntimo) y en **API Keys** crea una clave. Copia la clave (empieza por `sk-ant-`).
2. En PythonAnywhere abre una consola **Bash** y escribe: `pip3 install --user anthropic`
3. En el archivo WSGI, debajo de las otras líneas `os.environ[...]`, añade:
   `os.environ["WEBLIFE_CLAUDE_CLAVE"] = "pega-aqui-tu-clave"`
4. **Save** y **Reload**.

Nunca escribas esa clave en el código ni en GitHub: solo en el archivo WSGI.

## Cosas que debes saber

- **Renovación:** en la cuenta gratis, la web se apaga después de 3 meses si no la renuevas. Entra a la pestaña **Web** y haz clic en **Run until 3 months from today** de vez en cuando (PythonAnywhere te avisa por correo).
- **Tus datos:** la web en internet empieza vacía. Lo que guardaste en tu Mac queda en tu Mac.
- **Si algo falla:** en la pestaña **Web**, abre el **Error log**. Ahí aparece el error, y puedes pegármelo.
- **Para actualizar el código:** sube el archivo que cambiaste en **Files** (por ejemplo `app.py`) y vuelve a hacer clic en **Reload**. Nunca subas ni borres `weblife.db`, porque ahí están tus datos.
- **El código de invitación** solo está en el archivo WSGI de tu cuenta. Si lo cambias, quien ya tenga cuenta sigue entrando normal; solo cambia para las cuentas nuevas.
- **Cuentas:** cada persona tiene su usuario y contraseña, y solo ve sus propias clases, tareas y asistencia. La primera cuenta que se crea se queda con los datos que había antes de que existieran las cuentas.
