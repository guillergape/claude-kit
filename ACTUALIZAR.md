# Actualizar el kit — `actualiza kit >`

<!-- Lo sigue el Claude de la persona que instaló el kit. Se lee SIEMPRE de la versión nueva (después del git pull o en kit-nuevo/), así el procedimiento también se actualiza. -->

Cuando la persona escriba `actualiza kit >` (o lo pida con otras palabras). **La primera respuesta es solo la revisión (pasos 1–3): no apliques nada hasta el OK del paso 4.**

## Reglas
1. **Solo se aplica lo que cambió en el kit, y solo en lo que la persona tiene instalado.** Un componente nuevo se ofrece; no se instala sin que lo pida (entonces se sigue su fase de `kit/CLAUDE.md`).
2. **Lo que la persona cambió se respeta.** Si una copia instalada no es igual a lo que puso el kit, no se sobrescribe: se fusiona enseñándole el resultado, o se le pregunta.
3. **Mismo rastro que al instalar** (regla 3 de `kit/CLAUDE.md`): copia `.bak-AAAA-MM-DD` antes y `.kit-AAAA-MM-DD` justo después de cada cambio global, marcas `<!-- kit:… -->`, JSON validado, nada global sin enseñar el cambio exacto.
4. **Idioma** (`IDIOMA` en `kit-datos.yaml`, regla 11 de `kit/CLAUDE.md`): si no es `es`, las copias instaladas de texto están traducidas. Entonces compáralas por contenido, no línea a línea, y aplica el cambio del kit **traducido**; el 🟢/🟡 sale de comparar con el `.kit-` o la copia que dejó la instalación, no con el kit en español.
5. **Nunca edites `<LAB>/kit/`** salvo para ponerlo en la versión nueva (git pull / cambiar la carpeta del zip).

## Paso 1 — Traer la versión nueva (si no se hizo ya)
- **Con git** (`kit_commit` no vacío en `<LAB>/kit-datos.yaml`): `VIEJA = kit_commit`. Si `git -C <LAB>/kit status --porcelain` no está vacío, alguien editó el kit: enséñalo y pregunta antes de seguir (lo normal es mover esos cambios a la copia instalada y `git -C <LAB>/kit checkout -- .`). Luego `git -C <LAB>/kit pull --ff-only`. `NUEVA = HEAD`.
- **Sin git**: el zip nuevo descomprimido en `<LAB>/kit-nuevo/` (dentro trae una carpeta: usa la que tenga `VERSION.txt`). `VIEJA = <LAB>/kit/`, `NUEVA = <LAB>/kit-nuevo/`.
- Si `VERSION.txt` de la nueva es igual a `kit_version`: «Ya tienes la última versión (…)». Fin.

## Paso 2 — Qué cambió
1. **Novedades:** las entradas de `CAMBIOS.md` de la versión nueva posteriores a `kit_version`, tal cual (están escritas para la persona).
2. **Ficheros:** con git `git -C <LAB>/kit diff --stat VIEJA NUEVA` (y `git log --oneline VIEJA..NUEVA`); sin git, compara las dos carpetas (Python `filecmp.dircmp`, recursivo; ignora `desktop.ini`, `__pycache__`, `VERSION.txt`).
3. Cruza cada fichero cambiado con la lista `instalado:` de `kit-datos.yaml` (formato `origen -> destino`; un origen `plantillas/CLAUDE.global.md#kit:<sección>` es esa sección del CLAUDE.md global). Quedan tres grupos: **instalado y cambiado**, **nuevo en el kit** (no instalado), **ya no está en el kit**. Lo que cambió pero no está instalado (guías, plantillas que no usó) solo se menciona en una línea.

## Paso 3 — Revisión (sin cambios)
Para cada fichero **instalado y cambiado**, mira si la persona lo tocó:
- `viejo_rellenado` = el fichero en la versión VIEJA (`git -C <LAB>/kit show VIEJA:<origen>` o `<LAB>/kit/<origen>`) pasado por `rellenar.py` con su `kit-datos.yaml`; `nuevo_rellenado` = lo mismo con la NUEVA.
- **Scripts y SKILL.md**: copia instalada == `viejo_rellenado` → 🟢 **intacto**: se sustituye por `nuevo_rellenado`. Distinta → 🟡 **cambiado por la persona**: fusión a tres bandas (`git merge-file -p <instalado> <viejo_rellenado> <nuevo_rellenado>`; sin git, a mano) y se enseña el resultado; si hay conflicto, se le enseñan las dos versiones de ese trozo y elige.
- **Secciones del `CLAUDE.md` global** (`<!-- kit:x -->…<!-- /kit:x -->`): compara la sección actual con la del último `.kit-` (lo que dejó el kit). Igual → 🟢: se aplica el cambio de la plantilla (diff `viejo_rellenado` → `nuevo_rellenado` de esa sección) **conservando los `<…>` que rellenó con él**. Distinta → 🟡: enseña su cambio y el del kit lado a lado y pregunta.
- **`settings.json`**: compara en JSON (Python, no a ojo) el fragmento viejo y el nuevo rellenados; solo se añaden/quitan/cambian esas entradas, y solo si siguen como las dejó el kit (`.kit-`).
- Ficheros de datos de la persona (`carpetas.json`, `moodle.json`, CSV, `personas.md`, `leftover.md`, `INFORME_MIGRACION.md`) **nunca se sustituyen**; si el ejemplo del kit trae una clave nueva, se propone añadirla.

Enséñale: las novedades (paso 2.1), una tabla `componente · qué cambia · 🟢/🟡 · qué haré`, lo nuevo que podría instalar (una línea cada uno, con su «¿te funcionará?») y lo que ya no está en el kit (se queda instalado salvo que diga otra cosa). Pregunta: aplicar todo 🟢 · elegir · nada; y una decisión por cada 🟡.

## Paso 4 — Aplicar
1. Copias `.bak-` de todo lo que se va a tocar.
2. Aplica lo elegido. Para cada script cambiado, su `--test` debe decir `ok`; si falla, deja la copia anterior (`.bak-`), apúntalo y sigue (los fallos largos → *Chats aparte*, regla 9 de `kit/CLAUDE.md`).
3. Componentes nuevos que pidió: sigue su fase de `kit/CLAUDE.md` y añádelos a `instalado:`.
4. Copias `.kit-` nuevas de los ficheros globales tocados.
5. Sin git: `<LAB>/kit/` → `<LAB>/kit-AAAA-MM-DD-viejo/` (a la papelera cuando todo funcione) y `<LAB>/kit-nuevo/<carpeta>` → `<LAB>/kit/`.
6. En `kit-datos.yaml`: `kit_version` = línea de `VERSION.txt` nueva; `kit_commit` = `git -C <LAB>/kit rev-parse HEAD` (vacío sin git).

## Paso 5 — Comprobar y apuntar
1. Si cambió algún hook o la status line: que reinicie Claude Code y escriba algo (sin errores de hooks; status line visible).
2. En `<LAB>/INFORME_MIGRACION.md`, sección *Actualizaciones*: fecha, versión vieja → nueva, qué se aplicó, qué se fusionó, qué dejó sin aplicar y por qué, fallos.
3. Si hubo algo que reportar al autor del kit (un fallo, una fusión difícil), díselo en una línea: puede mandarle el informe.
