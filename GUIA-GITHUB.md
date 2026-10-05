# Actualizar tu web con GitHub

**La idea:** yo guardo cada cambio en GitHub (una carpeta en internet). Tú le dices a PythonAnywhere "trae lo nuevo" y aprietas Reload.

```
Claude cambia el código  →  GitHub  →  PythonAnywhere (git pull + Reload)  →  tu web
```

---

## Parte 1: crear GitHub (una sola vez, ~5 minutos)

1. Entra a **https://github.com** y haz clic en **Sign up**. Crea tu cuenta con tu correo.
2. Ya dentro, haz clic en el **+** (arriba a la derecha) → **New repository**.
   - **Repository name:** `weblife`
   - Elige **Public**. Tu código no tiene contraseñas (la contraseña vive solo en PythonAnywhere), y así PythonAnywhere puede descargarlo sin pasos extra.
   - **No** marques "Add a README".
   - Haz clic en **Create repository**.
3. Conecta GitHub con Claude: abre https://claude.ai/connect-github y acepta.
4. Instala la app de Claude en tu repositorio: abre https://github.com/apps/claude/installations/select_target, elige tu cuenta, marca **Only select repositories** → `weblife` → **Install**.
5. Escríbeme en el chat: **"listo, mi usuario de GitHub es ____"**.

Yo subo el código y te aviso.

---

## Parte 2: conectar PythonAnywhere con GitHub (una sola vez)

Cuando te avise que el código está en GitHub, abre una consola **Bash** en PythonAnywhere y pega estas líneas, una por una (cambia `TU-USUARIO-GITHUB`):

```
mv weblife weblife-viejo
git clone https://github.com/TU-USUARIO-GITHUB/weblife.git
cp weblife-viejo/weblife.db weblife/
```

- La primera línea guarda tu carpeta actual con otro nombre (por si acaso).
- La segunda descarga el código desde GitHub.
- La tercera copia tus datos a la carpeta nueva. Si dice "No such file", no pasa nada: es que todavía no habías guardado nada.

Luego ve a **Web** → **Reload**. Tu archivo WSGI no cambia: sigue apuntando a `/home/weblife/weblife`.

---

## Parte 3: cada vez que te pida un cambio

1. Me pides el cambio en el chat ("pon el fondo oscuro", "cambia los colores"...).
2. Yo lo hago, te muestro una captura y lo subo a GitHub.
3. Tú abres una consola **Bash** en PythonAnywhere y pegas:
   ```
   cd ~/weblife && git pull
   ```
4. Ve a **Web** → **Reload**. ¡Listo!

Tus datos (`weblife.db`) nunca se suben a GitHub ni se borran con `git pull`.
