# login> — cambiar la cuenta de Claude Code (0 tokens)

Para quien tiene varias cuentas de Claude (p. ej. personal y de la uni/trabajo). Escribe en cualquier chat `login> <cuenta>`: el hook `costlog/costlog.py` bloquea el mensaje (Claude no lo ve) y abre `login.py` en una ventana propia (Windows; en Mac/Linux el hook te da el comando para una terminal).

⚠ Las credenciales de Claude Code son compartidas: **todos los chats abiertos en el ordenador** pasan a la cuenta nueva.

## Qué hace
1. **Tus cuentas** (las de `login.json`; vale el email entero o solo lo de antes de la @) van directas.
2. **Erratas de esas** (una letra de más o de menos, `@gamil.com`…): «¿Te referías a X? [y/n]».
3. **Cualquier otra dirección**: «Has escrito: X. ¿Es correcto? [y/n]». Luego, Gmail: que el nombre pueda existir (6–30 letras, números o puntos); otro dominio: que reciba correo (MX). Que el buzón exista no se puede comprobar.
4. Si ya estás en esa cuenta, lo dice y para.
5. Al final, `claude auth status --json` comprueba que es la cuenta pedida y que tiene **suscripción** (pro/max/team/enterprise).

## Modo automático (Windows, cuentas de `login.json`)
Sin tocar el ratón ni teclear el código del correo:
- `claude auth login --claudeai --email X` se lanza con `BROWSER` = un script que solo guarda la URL de autorización (no se abre tu navegador).
- `click.py` abre esa URL en un **Edge fuera de pantalla con un perfil propio por cuenta** (carpeta `perfiles` de `login.json`) y pulsa con UI Automation:
  - Perfil ya con sesión en claude.ai: solo **Authorize**.
  - Si no: escribe el email (nunca una contraseña: claude.ai no tiene), «Continue with email», **lee el correo de claude.ai en el Gmail de esa cuenta** (según `gmail` en `login.json`), abre el enlace en el mismo perfil, lee el **código de 6 cifras** que muestra, vuelve a la primera pestaña, lo escribe y verifica. Luego Authorize. El código y el enlace nunca se guardan en `login.log` (salen como `######`).
  - **Un solo correo por ejecución**: si tras el enlace vuelve la página de inicio de sesión, para (varios seguidos hacen que claude.ai diga «demasiados intentos»; sale con código 5 y lo dice).
  - claude.ai deja Authorize desactivado mientras su pestaña no tiene el foco: `click.py` espera a que no teclees, da el foco a ese Edge (sigue fuera de pantalla) unos segundos, pulsa y te devuelve el foco. Si tecleas justo en ese momento, esas teclas van a Edge.
  - **Casilla de Cloudflare** («¿eres humano?»): el script **nunca la marca**. La ventana se pone delante, la marcas tú y sigue solo (hasta 5 min).
- Si `click.py` no puede, abre la misma página en una **ventana visible** de ese perfil y terminas tú.
- Al acabar, un proceso aparte cierra ese Edge a los 35 s (para que guarde las cookies de claude.ai). Tu Edge normal no se toca nunca.

## Instalar
1. Copia `kit/login/` → `<LAB>/login/`. Necesita `costlog/` en `<LAB>/costlog/` (el hook, y `send.py` si alguna cuenta usa `"gmail": "send"`).
2. `login.example.json` → `<LAB>/login/login.json` con **sus** datos (pásalo por `rellenar.py` para `<HOME>`): sus cuentas y, para cada una, cómo se lee su Gmail:
   - `"send"`: la cuenta ya está autorizada en el MCP `google-workspace` (fase 6); usa los mismos tokens que `send.py`.
   - `"vault"`: sin MCP. Una vez: `<PY> <LAB>/login/login.py --gmail-auth <email>` abre el navegador, la persona permite **solo lectura** de Gmail y el token va al vault (`vault/`, hace falta instalado; nunca se imprime). Con solo lectura, el correo de claude.ai se queda sin leer en su Gmail.
   - `"no"`: no se lee; el inicio de sesión lo termina la persona en la ventana visible (p. ej. una cuenta de otra persona).
3. Modo automático: `uv` instalado (lo usa para traer `uiautomation` sin instalarlo) o `<PY> -m pip install uiautomation`; Edge en la ruta de `edge`.
4. Prueba: `<PY> <LAB>/login/login.py --test` → `ok`; `<PY> <LAB>/login/login.py --dry-run <una cuenta suya>` → dice lo que haría sin cambiar nada. La primera vez de verdad, que la persona lo vea (cambia la cuenta de todos sus chats).
5. Si su claude.ai sale en otro idioma (ni inglés ni español), rellena el bloque **TEXTOS DE CLAUDE.AI** de `click.py` con los nombres de los botones: `login.log` lista los controles de cada página.

## Probado
- En el ordenador del autor del kit (Windows 11, 29 oct 2026), con su versión de este script: cambio real entre dos cuentas con el código del correo leído solo, y erratas («¿Te referías a…?»), ya estando en la cuenta, Cloudflare.
- Esta versión genérica (configuración en `login.json`): solo `--test` y `--dry-run`; el modo automático **¿?** hasta la primera prueba de alguien. **Mac/Linux:** solo el modo manual (`claude auth login`), sin probar.
- Los mensajes de `login.py` salen en español.
