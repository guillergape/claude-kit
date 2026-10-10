# keep-awake: que Claude siga trabajando cuando dejas el portátil

**Solo hay versión para Windows.** Mac y Linux: ver la última sección (idea sin probar).

Hook global de Windows (`keep-awake.ps1`; viene como `keep-awake.ps1.txt` porque Gmail bloquea adjuntos `.ps1`: renómbralo). Se registra en `~/.claude/settings.json`: `UserPromptSubmit` → `… keep-awake.ps1 start`, y `Stop` / `StopFailure` / `SessionEnd` → `… keep-awake.ps1 stop` (bloque listo en `plantillas/settings.fragment.json`).

## Qué hace
- Mientras Claude trabaja, un proceso oculto (`keeper`) pide a Windows `ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`: el PC no se suspende ni apaga la pantalla por inactividad.
- Para ahorrar batería: tras **3 min sin tocar nada con batería / 5 min enchufado** → brillo 0 (el terminal se sigue leyendo). Tras **otros 3 / 5 min** → pantalla negra estática con un pequeño símbolo de Claude.
- Cualquier tecla / ratón → vuelve el brillo que tenías antes y se cierra la pantalla negra.
- Si Claude termina mientras no estás, la pantalla oscura sigue hasta que toques algo; luego mandan los tiempos normales de Windows.
- Se rinde solo si el chat lleva 30 min sin escribir nada (atascado o esperándote) y como mucho a las 8 h.

## Por qué no simplemente "apagar la pantalla"
En portátiles con **Modern Standby** (S0 low power idle; míralo con `powercfg /a`), **apagar la pantalla ES la suspensión**: todos los procesos de escritorio se congelan, Claude incluido, aunque se pida `ES_SYSTEM_REQUIRED` (probado: 311 s congelado). Por eso el hook baja el brillo y pone negro en vez de apagar. Con S3 clásico no pasa, pero el hook sigue siendo útil para que no se suspenda.

## Cosas comprobadas (no repetir)
- El brillo se cambia sin admin por WMI (`WmiMonitorBrightnessMethods.WmiSetBrightness`). En monitores externos de sobremesa suele no existir: entonces solo hace la pantalla negra.
- En LCD el negro en sí no ahorra (la retroiluminación = brillo); por eso primero brillo 0 y la pantalla negra es **estática** (el spinner de Claude Code mantiene el panel refrescando).
- Los salvapantallas de Windows no sirven: `ES_DISPLAY_REQUIRED` los bloquea y no bajan el brillo.
- Cerrar la tapa **sí** suspende (eso no lo puede impedir un programa).
- Bug histórico: en PowerShell 7 `0x80000003` es un Int32 negativo y la llamada fallaba en silencio (ventana oculta), así que el hook no hacía nada. Esta copia usa `[uint32]2147483651`, que vale en PowerShell 5.1 y 7.
- Errores amarillos "API Error … connection" no son siempre suspensión: pueden ser cortes de Wi-Fi. Para distinguirlo: `Get-WinEvent` del log System (Kernel-Power 506/507 = entra/sale de Modern Standby) y `Microsoft-Windows-WLAN-AutoConfig/Operational` (11004/11005 = reautenticación Wi-Fi) alrededor de la hora del error.

## Comprobar que funciona
Con Claude trabajando: `powercfg /requests` debe mostrar el proceso de PowerShell en SYSTEM y DISPLAY. Ajustes al principio del script (`$IdleDC`, `$IdleAC`, `$StaleMinutes`, `$MaxHours`).

## Mac y Linux — sin versión todavía (idea sin probar)
Si la persona lo quiere, se hace en un **chat aparte** (regla 10 de la guía) y se apunta en el informe para que el autor lo añada al kit.
- **Mac:** `UserPromptSubmit` → lanzar en segundo plano `caffeinate -dimsu` y guardar su PID; `Stop` / `StopFailure` / `SessionEnd` → matarlo. Brillo: no hay orden de serie (`brightness` de Homebrew). Cerrar la tapa suspende salvo con pantalla externa y corriente.
- **Linux:** `UserPromptSubmit` → `systemd-inhibit --what=idle:sleep --why="Claude trabajando" sleep infinity` en segundo plano, guardando el PID; los `stop` → matar ese PID. Brillo: `brightnessctl` (sin root si el usuario está en el grupo `video`). En Hyprland/Sway la inactividad la gestiona `hypridle`/`swayidle`: comprobar que respetan el inhibidor de systemd. Cerrar la tapa sí suspende; eso no lo impide ningún programa sin cambiar `logind.conf`.
- Lo que hay que conservar del de Windows: que se rinda solo (30 min sin escribir nada o 8 h como mucho) y que el `stop` no falle si no hay nada que parar.
