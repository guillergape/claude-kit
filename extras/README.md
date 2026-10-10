# extras (opcionales, 0 tokens)

## `old.py`: versiones viejas y papelera que se vacía sola
Idea: nunca pierdes una versión anterior y lo que tiras se puede recuperar un tiempo, sin acumular basura.
- `<PY> old.py archive <fichero>` → **copia** a `old/<nombre>_AAAA-MM-DD.<ext>` en la misma carpeta (historial que se queda; úsalo antes de rehacer algo que ya entregaste o enviaste, p. ej. un CV o un informe).
- `<PY> old.py trash <fichero>` → lo **mueve** a `_papelera/` en la misma carpeta.
- `<PY> old.py purge <carpeta raíz> [--days 60]` → borra lo que lleva más de N días en cualquier `_papelera/` debajo de esa raíz.
- Para que sea automático: un hook `SessionStart` que ejecute `purge` (bloque en `plantillas/settings.fragment.json`). No imprime nada si no borra nada.
- La regla para Claude (en el CLAUDE.md global): "antes de sobrescribir algo ya entregado/enviado, `archive`; para borrar algo de mis carpetas, `trash` (o la Papelera de reciclaje), nunca borrado definitivo".
- `<PY> old.py --test` = autocomprobación.

## `timelog.py`: cronometrar sesiones de estudio
`start <asig> <cmd> <ref>` · `lap <asig> "<sección>"` · `end <asig> [--minus N | --total N | --from HH:MM | --na]` · `report [asig]`. Guarda `timelog.csv` y `timelog_state.json` junto al script (o en `$TIMELOG_DIR`). Sirve para saber cuánto tarda cada tema/práctica y planificar exámenes.
El original lo arrancaba un hook `UserPromptSubmit` cuando el prompt era un comando de estudio (p. ej. `Prog study T2 >`) y lo paraba con `fin de la sesión >`; ese hook dependía de su sistema de apuntes, así que no se incluye: si lo quieres, pide a Claude un hook equivalente para tus comandos.
