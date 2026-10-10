# La uni con Claude (cómo lo organiza el autor del kit, adaptable)

Son ideas probadas en un doble grado de ingeniería; tu Claude debe **preguntarte** cuáles quieres antes de montarlas, porque dependen de cómo estudias.

## Moodle por API (módulo `moodle`, 0 navegador)
Módulo opcional: ver `modulos/moodle/SKILL.md`. Resumen: un token de la app móvil de Moodle guardado fuera de cualquier repo; `moodle.py new|due|dates|get|post|seen|courses`; el comando `moodle >` resume material nuevo, avisos, entregas pendientes y fechas, y ofrece descargar lo importante y meter fechas en el calendario. Las descargas caen en una bandeja temporal y luego se archivan en la carpeta de cada asignatura **sin sobrescribir nunca**.
- Si el login de tu Moodle es por SSO de la universidad, `login/token.php` no sirve: se saca el token con `admin/tool/mobile/launch.php` (pasos en el SKILL.md).
- Orden general para cualquier web: **1) API o script, 2) navegador (Claude in Chrome) leyendo texto/DOM sin capturas, 3) capturas y clics como una persona solo si lo demás falla** (las capturas gastan muchos tokens).

## Estructura de carpetas (ejemplo)
- Una carpeta por curso y dentro **una por asignatura, cada una con su propio `CLAUDE.md`** (de qué va, fuentes principales, evaluación, normas propias). Arrancar Claude **dentro** de la carpeta de la asignatura hace que actúe como "profe" de esa asignatura con su propio historial.
- En cada asignatura: `00_Guia/` con `Main sources.md` (qué sigue el curso, evaluación, fechas, y una línea **Status** confirmado/pendiente) y una tabla **Clases dadas** (fecha · tema · si fuiste · qué se vio → dónde se quedó · fuente), luego solo las carpetas que tengan contenido (`Teoria/`, `Problemas/`, `Practicas/`, `Examenes/`…). No crear carpetas vacías.
- Los documentos que genera Claude, en **una sola carpeta** por asignatura (p. ej. `Apuntes (Claude)/`), en PDF, con la fuente `.md` en un `_fuente/` al lado (skill `md2pdf`). Nombres en ASCII con semana/tema y tema corto: `notasCLI S2 Punteros.pdf`, `ejsCLI S2 Punteros.pdf`, `esqCLI S1-3 Recursion.pdf`.

## Comandos (todos acaban en `>` para que se distingan de una conversación)
- `<Asig> >`: sesión completa (sincroniza Moodle, revisa archivos nuevos en la carpeta, lee `Main sources.md` y sigue donde va la clase). `<Asig> nosync >`: lo mismo sin sincronizar.
- `<Asig> qq >` / `qq >`: **pregunta rápida**: responde y no cambia nada (si la pregunta pide un cambio, lo sugiere y espera "hazlo").
- `_<carpeta>:` (modo carpeta, hook `carpetas.py`): trabajar solo en esa carpeta hasta `exit >`.
- Comandos de estudio por semana: `edit <Sn> >` (leer unos apuntes de Claude preguntando; al final integra las respuestas en el texto), `study <Sn> >` (resolver dudas sin tocar los apuntes), `help ejs <Sn> >` (corrige tus ejercicios y lleva un tracker), `create notes|ejs|esq <Sn> >` (genera apuntes / ejercicios resueltos / esquema y tú los revisas).
- `progress >` (skill `progress`), `fin de la sesión >` (aplica los cambios en cola, regenera el PDF y guarda el progreso en memoria).
- Un mensaje que parece un comando pero sin `>` no se ejecuta: Claude pregunta en una línea.

## Estudio orientado a examen
- Ordenar fuentes de examen por fiabilidad: (1) exámenes pasados del **mismo profe**; (2) problemas que el profe marcó como tipo examen; (3) exámenes antiguos de otros profes; (4) hojas de problemas genéricas. Apuntarlo en `Main sources.md`.
- Con material fiable: mapear qué tipos de problema salen y cuánto, y centrar apuntes y explicaciones en lo necesario para resolverlos. Lo demás se marca **[NO EXAMEN]** (no se borra en silencio).
- Ejercicios: primero los hechos en clase; uno resuelto entero por tipo y los demás del mismo tipo solo con datos y resultado; soluciones en caja.

## Sesiones largas sin perder nada
- Fichero de sesión `_session <cmd> <ref>.md` con la lista de cambios en cola y dónde vas: así puedes hacer `/clear` cuando el chat crece y retomar escribiendo otra vez el comando. Un `/clear` cuesta ≈ 20–25k tokens de releer, y ahorra reenviar todo el contexto anterior en cada mensaje: compensa tras una o dos preguntas más.
- "Ponlo en los apuntes" = a la cola; solo "hazlo ya" edita al momento. Al final de la sesión se aplica todo de una vez.
- Leer ficheros grandes por secciones (`grep -n '^#'` y leer solo la sección), no enteros.
- Modelo: preguntas/estudio con Opus medium; crear documentos o revisiones finales con Opus high.

## Wuolah (exámenes pasados)
- Solo páginas **de tu universidad** (nunca de otras, aunque sea la misma asignatura). Buscar la asignatura en español e inglés en "Asignaturas" y mirar otros grados de tu uni que la compartan (cada grado es una "community" con su id en la URL `?communityId=…`).
- **Nunca gastar monedas**: solo "Descargar PDF con publi" (0 monedas). "Sin publi" cuesta monedas; "Descargar carpeta" es Pro (ir fichero a fichero). Ficheros de más de 50 MB son solo Pro: saltarlos y avisar.
- Primero la lista de posts/ficheros (exámenes / trabajos / apuntes) y **descargar solo lo que apruebes**.
- **Descarga en paralelo (comprobado):** con pop-ups permitidos para wuolah.com, abrir **cada fichero en su propia ventana pequeña** desde una pestaña de Wuolah con `window.open(url, name, 'popup=yes,width=331,height=232,left=X,top=Y')` (URL de fichero: `wuolah.com/apuntes/<asignatura>/<post>-<fichero>-pdf-<id>`). Son del mismo origen, así que se manejan desde la pestaña que las abrió: un `.click()` simple se ignora, hay que disparar `pointerdown/mousedown/pointerup/mouseup/click`. Colocarlas en mosaico (p. ej. 4 × 3) y fijarlas encima con `SetWindowPos` desde PowerShell: **la cuenta atrás de 60 s solo avanza si la ventana se ve de verdad**, y cualquier ventana encima la congela. Así todas las cuentas atrás corren a la vez y el botón final **Descargar** se pulsa también por script, **una vez** (dos = duplicado `… (1).pdf`). Los posts con varios ficheros no tienen `<a href>`: leer las props de React del feed (`artifacts[].documentCatalog[].slug`).
- **Límite:** tras ~15 descargas en pocos minutos, Wuolah corta (`api.wuolah.com/v2/download` → **429 `{"code":"FI008"}`**, "Sabemos que no eres un robot"). Ni recargar ni esperar 25 min lo arregló: probablemente cupo diario. Lotes de ~10 con unos minutos entre ellos; al primer 429, parar y seguir al día siguiente.
- Caen en Descargas como `wuolah-free-<nombre>.pdf`: moverlos (sin sobrescribir) a `<Asignatura>/Examenes/Wuolah/` con nombre `<Asig>_<parcial1|parcial2|final|extraordinaria>_<AAAA>_<MM>[_G<grupo>][_con-sol|_sol].pdf` (`_con-sol` = enunciado + solución; `_sol` = solo solución). Fecha y tipo sacados del propio documento, no del título de Wuolah.

## Otros trucos de la uni
- Guías docentes oficiales suelen tener URL pública por código de asignatura: guardar el enlace en `Main sources.md`.
- `.ppt`/`.docx` antiguos de profes → convertir a PDF (con Office instalado vale por COM) para que Claude los lea.
- Para leer PDFs: renderizar páginas a PNG con PyMuPDF (`pymupdf.open(f)[i].get_pixmap(dpi=100).save(png)`) y leer las imágenes; `pdftoppm` no viene en Windows.
