# terminal-favoritos — tus comandos `cd "<carpeta>"; claude` en la flecha arriba

Con el prompt vacío, **flecha arriba** muestra primero tus comandos favoritos (los que más repites para entrar en una carpeta y abrir Claude) y, tras el último, sigue el historial normal. **Flecha abajo** vuelve: historial → último favorito → … → primer favorito → prompt vacío. Con texto escrito (o tras editar un favorito) las flechas funcionan como siempre. Los favoritos **no se guardan en el historial** (no se duplican); solo se insertan en el prompt. El estado se reinicia en cada prompt nuevo. Cada terminal tiene su propio historial: lo que escribes en otra no se cuela.

Solo PowerShell con PSReadLine (PowerShell 7 recomendado; en Windows PowerShell 5.1 sin probar). La lista es `favoritos.txt` (un comando por línea; `#` = comentario) junto a `favoritos.ps1`. Sin lista, el script no hace nada.

## Instalar (Claude, con la regla 3 de `kit/CLAUDE.md`)
1. Copia `kit/extras/terminal-favoritos/` → `<LAB>/extras/terminal-favoritos/`.
2. **Genera la lista, nunca fija:** `<PY> <LAB>/extras/terminal-favoritos/detectar.py` mira el historial de PSReadLine de **esta** persona (`(Get-PSReadLineOption).HistorySavePath`), cuenta los comandos del tipo `cd "<carpeta>"; claude` (también `cd x && claude`, `Set-Location`, `sl -Path`, con argumentos como `--resume`) y enseña los 4 más repetidos cuya carpeta **existe hoy** (`-n 6` para más). No escribe nada.
   - Si no hay historial o no sale nada útil, `detectar.py` lo dice: **pregúntale qué carpetas quiere** y genera las líneas con `detectar.py --folders "<carpeta1>" "<carpeta2>" …` (comprueba que existen).
3. **Enséñale la lista y espera su OK o sus cambios.** Solo entonces repite el mismo comando añadiendo `--write` (crea `favoritos.txt` junto al script). Si cambia algo, edita `favoritos.txt` a mano.
4. Añade esta línea **al final de su perfil de PowerShell** (`$PROFILE`; enséñale el cambio y haz antes copia `.bak-AAAA-MM-DD`; si el fichero no existe, se crea):
   ```powershell
   if ($env:TERM_PROGRAM -eq 'vscode') { . "<LAB>/extras/terminal-favoritos/favoritos.ps1" }
   ```
   El `if` limita el efecto a las terminales de VS Code; si usa otra terminal (Windows Terminal…), pregúntale y quita el `if`. Qué cambia: reasigna flecha arriba/abajo (PSReadLine) y envuelve la función `prompt` (misma salida, más un reinicio de estado).
5. Apunta en `kit-datos.yaml` → `instalado:` `extras/terminal-favoritos/ -> <LAB>/extras/terminal-favoritos/` y la línea del perfil en el informe (*Cambios hechos fuera de la carpeta del lab*).
6. Prueba: `<PY> <LAB>/extras/terminal-favoritos/detectar.py --test` → `ok`. En **Windows**: `<PY> -m pip install pywinpty` y `<PY> <LAB>/extras/terminal-favoritos/test_tui.py` → `ok` (≈1 min; abre dos PowerShell ocultos con un historial falso en una carpeta temporal, no toca su perfil ni su historial real; 0 tokens). Luego que abra una terminal nueva de VS Code y pulse flecha arriba.

## Para actualizar con `actualiza kit >`
`favoritos.txt` es **suyo**: nunca se sobrescribe; solo `favoritos.ps1`, `detectar.py` y `test_tui.py`.

## Lecciones de PSReadLine (para el siguiente test)
- No observes el prompt con otro atajo extra (p. ej. F12): cualquier handler entre dos flechas reinicia la posición del historial y parece «atascado». El test usa un gancho `FavTrace` al final de cada handler (`$global:FavTraceHook`; vacío en uso real).
- Escribe la línea del perfil en un `pwsh -NoProfile` interactivo (PSReadLine cargado), no con `-Command … -NoExit`, que reaplica los atajos por defecto.
- `RevertLine` durante la navegación devuelve la línea guardada; usa `Replace(0, largo, texto)`.
- Fija `Set-PSReadLineOption -HistorySavePath` **al lanzar** el proceso de un test, antes de teclear nada: si no, las líneas de prueba acaban en el historial real.
- No probado en la terminal integrada real de VS Code con este kit (el autor sí, con la suya); su integración de shell también envuelve `prompt` y el envoltorio encadena con ella.

## Quitarlo
Borra la línea del perfil (o vuelve a la copia `.bak-`) y la carpeta `<LAB>/extras/terminal-favoritos/`.

## Probado
Windows 11 + PowerShell 7 (autor del kit, 4–5 nov 2026): `test_tui.py` y `detectar.py --test` ok. Mac/Linux: `favoritos.ps1` y `detectar.py` deberían funcionar con PowerShell 7 (`pwsh`), pero `test_tui.py` usa pywinpty y no corre allí; sin probar.
