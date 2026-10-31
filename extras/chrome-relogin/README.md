# chrome-relogin: que Claude in Chrome vuelva a iniciar sesión solo

A veces la extensión **Claude in Chrome** pierde la sesión sin avisar y, cuando un chat intenta usarla, el chat se para hasta que la persona pulsa «Log in». `chrome_relogin.py` lo hace por ella: pulsa el «Log in» de la extensión y, si claude.ai lo pide, el «Authorize». 0 tokens, sin ratón ni capturas de pantalla.

**Requisitos:** **Windows + Microsoft Edge** (usa UI Automation; en Mac/Linux no existe esta versión) y `uv` (`uv run --with uiautomation`). La extensión de Claude instalada en Edge. No probado con Chrome.
**Estado honesto:** probado con una simulación (`sim/`: «Log in» → «Authorize» → conectada) y con la extensión ya conectada («already signed in»). **No se ha visto aún con una desconexión real**: si falla, `chrome_relogin.log` y `--dump` dicen qué ve.

## Instalación (la hace tu Claude, fase 8)
1. Copia `chrome_relogin.example.json` a `chrome_relogin.json` (junto al script) y pon en `email` **la cuenta de Claude de la extensión**. `profile` déjalo vacío: se autodetecta (la carpeta de perfil de Edge donde está instalada la extensión); si hay varias, escribe aquí la buena (`Default`, `Profile 1`…).
2. `uv run --quiet --with uiautomation python -I <LAB>/kit/extras/chrome-relogin/chrome_relogin.py --dump` → debe imprimir lo que ve en la página de la extensión (conectada: «Claude isn't available on this page»). Eso comprueba perfil, Edge y UI Automation sin pulsar nada.
3. Sin `--dump`: con la extensión conectada debe decir «already signed in» y no dejar ventanas ni pestañas.
4. Para la prueba de verdad, simúlalo: `python -m http.server 8770` dentro de `sim/` y, en una copia del script, cambia `PAGE` por `http://localhost:8770/login.html`. Debe salir «signed in», sin ventanas sobrantes.
5. Añade la sección `kit:chrome-relogin` de `plantillas/CLAUDE.global.md` al CLAUDE.md global.

## Uso
`uv run --quiet --with uiautomation python -I <LAB>/kit/extras/chrome-relogin/chrome_relogin.py` — salida 0 = conectada (o ya lo estaba) · 2 = no pudo (ver el log) · 3 = hace falta una persona (captcha, código o **otra cuenta**: trae su ventana delante). `--dump` (solo mira), `--dry-run` (solo detecta), `--loop N` (repite cada N s). Con la regla del CLAUDE.md global, el propio Claude lo lanza cuando la extensión falla y reintenta una vez.

## Cómo funciona y por qué
- Abre `chrome-extension://<id>/sidepanel.html` en una **ventana nueva de Edge de tu perfil** (nunca una pestaña en tu ventana: al cerrarla, Edge te cambiaría de pestaña) y la saca de la pantalla al instante. El código de la extensión envuelve la página en una puerta de login: sin sesión muestra «Log in»; con sesión, otra cosa.
- Busca los botones **por texto** (en/es/fr/de/it/pt), no por posición ni por píxel; si cambia el diseño, sigue valiendo mientras el texto sea parecido.
- **No te roba el foco:** (1) un hilo vigila el primer plano cada 5 ms y devuelve el foco si una ventana de Edge que no es tuya lo coge, salvo que acabes de tocar teclado/ratón; (2) la ventana oculta se «despierta» minimizándola y restaurándola **sin activarla** (`SW_SHOWMINNOACTIVE` / `SW_SHOWNOACTIVATE`), porque una ventana que nunca estuvo visible enseña la página en blanco a UI Automation; (3) solo el botón «Authorize» de claude.ai necesita foco (lo deja desactivado sin él): se pide con 1 s de teclado y ratón quietos y se corta a los 20 ms de cualquier pulsación.
- **No toca tus pestañas:** solo lee una pestaña **nueva** con «Claude/Authorize» en el título (por identificador de pestaña, no por título); no restaura pestañas salvo en una ventana tuya donde el script puso algo.
- **Se borra lo que crea:** al terminar (también con error, timeout o SIGTERM) cierra su ventana con WM_CLOSE y comprueba que desapareció; además hay un barrido de ventanas aparcadas/nuevas con solo pestañas vacías o de Claude (al empezar, para limpiar un kill duro, y al acabar).
- **Seguridad de cuenta:** si la página de claude.ai muestra un correo distinto del de `chrome_relogin.json`, **no pulsa Authorize** (vincularía la extensión a otra cuenta) y avisa. Sin correo configurado no comprueba la cuenta.
- **Con otra cuenta de Claude Code:** el script no mira con qué cuenta está Claude Code; solo actúa sobre la extensión de ese Edge. Si tienes varias cuentas, la extensión pertenece a una; desde las demás no se puede manejar y no hace falta lanzarlo.
- No escribe nada en ningún campo y solo pulsa «Log in» y «Authorize».

## Límites conocidos
- Windows + Edge. La ventana nueva se ve en pantalla unas decenas de ms al crearse; quien teclee en ese instante no pierde nada, pero puede notar un parpadeo en la barra de tareas.
- Si el diseño de la extensión o de claude.ai cambia mucho (otros textos), ajusta las expresiones `LOGIN` / `AUTH` del script.
- Un kill duro del proceso deja su ventana fuera de pantalla hasta la siguiente ejecución, que la cierra al empezar.
