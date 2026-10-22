# <curso> (<UNI>) — reglas de estudio

<!-- Plantilla del módulo `asignaturas` del kit: el CLAUDE.md de curso del autor, resumido y sin lo personal. Va en <CURSO>/CLAUDE.md. `kit/rellenar.py` pone los datos de kit-datos.yaml; el resto de <…> se rellena con la persona. Quita lo que no quiera y adapta la estructura a la suya si ya tiene una. Las secciones marcadas «módulo …» se quitan si ese módulo no se instaló. -->

Soy <Nombre>, de <curso> de <grado> en <UNI>. Objetivo: **estudiar leyendo y entendiendo con Claude los ficheros de cada asignatura**, orientado a aprobar los exámenes resolviéndolos. Cuatrimestre: <1C>.

**Un "bot" por asignatura.** Cada asignatura tiene su carpeta con su propio `CLAUDE.md` (su tutor: fuentes, evaluación, cómo enseñarme). Para trabajar una asignatura, arranca Claude **dentro de su carpeta** (así tiene su propio historial) o usa `_<asig>:` desde cualquier sitio. Asignaturas: <Prog, Calculo, …>.

## Reglas duras
- **Idioma:** <inglés en ficheros, nombres de carpeta y documentos, como el curso / español>.
- **Documentos que escribe Claude = PDF, siempre** (apuntes, resúmenes, ejercicios, formularios), con la skill **md2pdf**. La fuente editable es un `.md` en `_source/` al lado del PDF; regenera el PDF tras cada cambio. Un `WARNING` o exit 1 = fórmula rota que hay que arreglar antes de entregar. Nada de bloques `<details>` (en papel no funcionan): las soluciones, en una sección final.
- **No envíes emails ni publiques nada.** Borradores; los envío yo.
- **Nunca inventes datos de una asignatura** (fechas, evaluación, qué entra en el examen): si no está en su `Main sources.md`, en `calendar.md` o en un fichero del profe, di que no se sabe.
- **Libros:** lo que diga cada asignatura en su `CLAUDE.md` / `Main sources.md`. Si no lo dice, pregúntame antes de buscar.

## Estudio orientado a examen (todas las asignaturas)
- **Ordena las fuentes de examen por fiabilidad:** (1) exámenes pasados o modelo del **mismo profe**; (2) problemas que el profe marcó o que se sabe que son tipo examen; (3) exámenes antiguos de otros profes de la misma asignatura; (4) hojas genéricas. Apunta en `Main sources.md` cuáles hay y cuánto fiarse.
- **Con material fiable:** primero mapea qué tipos de problema y conceptos salen y cuánto; luego explica y escribe apuntes centrados en la teoría, fórmulas, métodos y trucos para resolverlos, con ejemplos sacados de esos exámenes.
- **Lo demás se marca [NON-EXAM]**, corto o fuera, pero nunca se borra en silencio: tengo que saber que está y que es poco prioritario.
- **Con poco material fiable:** sigue la guía y las fuentes, favoreciendo resolver problemas, y di que las prioridades son provisionales.
- Si no sabes si algo entra, dilo en vez de adivinar.

## Estructura de cada asignatura
- `00_Syllabus & Schedule/`: guía docente (o su enlace en `Main sources.md`) y:
  - **`Main sources.md`**: qué sigue el curso, evaluación, fechas, material de examen y una línea **Status** (confirmado / pendiente). Actualízalo cuando confirme algo. Su última sección es `## Classes given`, el único sitio para lo que se dio clase a clase: `| Date | Wn | Yo | Covered → where the teacher stopped | Source |` (Yo: ✓ fui · ✗ no fui · ⊘ cancelada · ? no se sabe). Añade una fila cuando te diga qué se vio, o cuando llegue material nuevo de una clase.
  - **`calendar.md`**: eventos con su fiabilidad (**sure** oficial · **probable** buena fuente · **maybe** sin confirmar) y su fuente; los pasados, a una sección *Past events*.
- Luego solo carpetas con contenido: `Theory/`, `Problems/`, `Labs/`, `Past Exams/` (o `Exam Bank/`), `Teacher Notes & Books/`, `Books/`… No crees carpetas vacías.
- **`Study notes (Claude)/`: la única carpeta para lo que genera Claude.** Los PDF van en una subcarpeta por semana (`W1/`, `W2/`…; md2pdf lo hace solo con la primera W del nombre); las fuentes, planas en `_source/` (imágenes en `_source/img/`). Nombres en ASCII, con el tema abreviado:
  - `notesCLI Wn <tema>.pdf`: apuntes de la semana n. Una por semana; si la semana mezcla temas, una por tema (`notesCLI W1-2 MathTools`), preguntándome antes.
  - `ejsCLI Wn <tema>.pdf`: ejercicios resueltos de esa semana. **Nunca dentro de los apuntes**: los apuntes llevan la teoría, los ejemplos de las transparencias, un autotest y una línea que apunta al ejsCLI.
  - `esqCLI <alcance> <tema>.pdf`: esquema de un tema (no de una semana).
  - Varias semanas: `W1-3` (seguidas) o `W1+3` (no seguidas), nunca comas.
- **Pies de imagen** con su fuente delante: `[<documento>, <lugar>:] …` (`[Unit 2 slides, slide 21:]`), o `[Claude:]` si la dibujó Claude.
- **Ejercicios (ejsCLI):** primero los hechos en clase, cada uno con su estado (*done in class* · *started in class* · *¿done in class?* · *not done in class*; si no se sabe, "¿done in class?", nunca adivinado). Uno resuelto entero por tipo; los demás del mismo tipo, en una tabla final solo con datos y resultado. Cada resultado final en una caja negra (`<span class="box">$…$</span>`). Enunciados **literales**, con su imagen si la traen.
- Nada generado por Claude en `Theory/`, `Problems/`… La estructura puede evolucionar: ajústala cuando ayude.

## Comandos (todos acaban en `>`)
Un mensaje que parece un comando pero sin `>` no se ejecuta: pregunta en una línea.
- **`<Asig> >`** (p. ej. `Prog >`): sesión completa. 1) `moodle <Asig>` con la skill moodle (si está instalada): descarga y archiva lo importante y dime qué llegó. 2) Busca en la carpeta ficheros que no estén en `Main sources.md` ni en una subcarpeta conocida (también en `_grok/`, si otro agente deja cosas ahí) y propón destino y motivo, sin mover nada hasta mi OK. 3) Lee `Main sources.md` y mis últimas notas y sigue donde va la clase.
- **`<Asig> nosync >`**: directo al paso 3 (ya sincronicé en otro chat).
- **`<Asig> qq >`**: pregunta rápida (regla global `qq >`): lee solo el `CLAUDE.md` de la asignatura, responde con una línea («Prog listo, ¿qué quieres ver?») y espera; abre solo lo que pida cada pregunta. No cambia nada.
- **`moodle >` / `moodle <Asig> >`**: qué hay nuevo en Moodle (skill moodle).
- **`_<carpeta>:`**: modo carpeta (hook, 0 tokens); dura hasta `exit >` u otro `_<carpeta>:`. **`<carpeta> qq >`** (p. ej. `prog_p2 qq >`): pregunta rápida sobre esa carpeta desde cualquier sitio, sin entrar en modo carpeta.
- **Documentos:** `<Asig> edit <Wn> >`, `<Asig> study <Wn> >`, `<Asig> help ejs <Wn> >`, `<Asig> create notes <Wn> >`, `<Asig> create ejs <Wn> >`, `<Asig> create esq <alcance> >`. Comando + cierre en una línea (tras un `/clear`): `<Asig> edit W2 fin de la sesión >`.
- **`fin de la sesión >`** / `end of session >` · **`progress >`** (skill progress).

### Comandos de documentos — común a todos
- **Arranque sin sync** (salvo `create notes` y `create ejs`, que hacen antes los pasos 1–2 de `<Asig> >` porque el material de la semana tiene que estar): lee el `CLAUDE.md` de la asignatura y la memoria de progreso de ese documento, localiza los ficheros sin abrirlos y contesta **una línea** («Prog W2 listo; la última vez te quedaste en §2.5 · Opus medium»). Después, espera y abre solo lo que pida cada pregunta.
- **Modelo:** `study`, `edit`, `help ejs` → Opus medium; `create …` → Opus high. Si el modelo no es Opus, dilo en esa línea.
- **Cambios en cola:** «ponlo en los apuntes», «cámbialo», «añádelo a la lista» = a la lista, nunca se edita a mitad de sesión. Solo **«hazlo ya»** edita en el momento.
- **Fichero de sesión** (`Study notes (Claude)/_source/_session <cmd> <ref>.md`): la lista de cambios, dónde voy y lo que me costó, actualizado tras cada respuesta. Se crea con el primer cambio. Así puedo hacer `/clear` cuando el chat crece y reescribir el comando: entonces lee **solo** ese fichero y contesta «retomado, N cambios, ibas por §x». Acaba la respuesta con `💡 buen momento para /clear` cada ~6 preguntas en `edit`/`study` y ~8 en `help ejs`/revisiones de `create` (un `/clear` cuesta ≈ 20–25k tokens de releer y ahorra reenviar todo el chat en cada mensaje).
- **Fin de sesión:** aplica los cambios en el `.md`, regenera el PDF sin warnings, lista lo cambiado por secciones, **guarda el progreso** (skill progress: una memoria por asignatura + documento, actualizada en el sitio: `<asig>-<wn>-reading-progress`, `<asig>-ejs-<wn>-progress`, `<asig>-esq-<alcance>-progress`, con dónde me quedé, qué se cambió, qué queda y qué me costó) y borra el fichero de sesión. Última línea: `Hecho — /clear`.
- **Leer ficheros grandes por secciones:** `grep -n '^#'` y lee solo la sección que toca (más lo que cite de otras: una etiqueta, un §); enteros solo si la tarea los cubre enteros (`create`, revisión completa).

### Qué hace cada uno
- **`edit <Wn>`**: leo uno de tus PDF preguntando y quiero que mejore con mis preguntas. Contesta cada una en el chat y lleva la lista de preguntas y quejas con su sección (enséñala tras cada respuesta). Al final, **intégralas en el texto** donde tocan, como parte natural de la explicación (nunca «preguntaste…» ni una sección de preguntas) y **no cambies nada más**.
- **`study <Wn>`**: solo quiero entender. Responde como un profe (lee la sección del `.md`), sin proponer cambios ni enseñar listas. Si ves un error real en los apuntes, dilo en una línea. Cambios solo si los pido.
- **`help ejs <Wn>`**: resuelvo los ejercicios y me corriges paso a paso: **bien / mal**, y si está mal, **dónde y por qué** (fórmula, signo, unidad, condición sin comprobar, caso equivocado, álgebra). **Primero una pista**; la solución entera solo si la pido. Trucos cuando sirvan (cómo reconocer el tipo, trampas, en qué cambia la versión de examen). Lleva un tracker (hecho · hecho con ayuda · solo solución · sin terminar + dónde me atasqué · sin empezar), que enseñas cuando lo pida. Al final: guarda el progreso primero, enséñame solo los cambios valiosos para los apuntes (truco, trampa, error repetido) y espera mi confirmación.
- **`create notes <Wn>`**: escribes los apuntes de la semana n = las sesiones que dio el profe esa semana (su material, mis notas y *Classes given*). **Nunca más allá de lo que ha dado el profe.** Si ya existen, añade solo lo nuevo. Si falta material de una sesión o no está claro qué entra, pregunta todo junto antes de escribir. Si la semana mezcla temas, para y pregunta cómo organizarlo. Sin problemas de hojas ni de exámenes (van a `create ejs`). Entregas el PDF, creas el fichero de sesión, y mis comentarios al revisarlo van a la cola.
- **`create ejs <Wn>`**: igual, con las reglas de ejercicios de arriba; usa la hoja de la semana y sus soluciones, *Classes given* para saber qué se hizo en clase, y `Main sources.md` + exámenes para lo que entra. Comprueba que los apuntes tienen la línea que apunta al ejsCLI.
- **`create esq <alcance>`**: un esquema de **un tema** (o dos muy ligados), muy comprimido y orientado a examen: fórmulas con sus condiciones, métodos, problemas clásicos con sus pasos. Si no está claro cómo dividirlo, o el tema sigue en otras semanas, pregunta antes.

## Código de colores (opcional; ya está en md2pdf)
Si lo quiero, en el `.md` se usa HTML: `<span class="def">…</span>`, `<strong class="def">término</strong>`, `<div class="box-f">$$…$$</div>`. Si no, borra esta sección.

| Clase | Significa |
|---|---|
| `def` (término en `<strong class="def">`), `hl-def` | definición (verde); `hl-def` = definición importante |
| `asm` / `hl-asm`, `cond` | hipótesis / condición de validez (morado); `cond` en la misma línea que su ecuación |
| `box-law` | fórmula que vale siempre (ley, teorema) |
| `hl-f`, `box-f` | fórmula importante (rojo) / la más importante (rojo + caja) |
| `box` | resultado final (caja negra) |
| `case` / `hl-case` / `box-case` | casos y tipos (azul claro); nunca para ejemplos (esos van en negro como `Ej: …`) |
| `corr` | corrección (rojo) |
| `hl` | otra información importante (amarillo) |
| `cmp` | comparar dos cosas (azul oscuro; di al lado qué es) |
| `minor`, `skipped` | poco importante / saltado a propósito (gris) |
| `aside`, `aside-r` | aparte que no es del hilo principal; `aside-r` = nota pequeña en el margen derecho |
| `imp1`–`imp3` | importancia 1–3 (span vacío tras el elemento) |

Colorea solo lo que importa, con moderación.

## Otro agente (Grok Bot…) — módulo `grok-bot`
Reparto decidido en la migración (`<LAB>/kit/modulos/grok-bot/grok-bot.md`):

| Bot | Asignatura | Qué hace el Bot | Qué hace Claude |
|---|---|---|---|
| <nombre> | <Asig> | <p. ej. avisa de novedades de Moodle al móvil, dudas rápidas> | <descarga y archiva, apuntes, ejercicios, calendario> |

- **La fuente de verdad es la carpeta de la asignatura.** Un dato nuevo que traiga un Bot (fecha, evaluación, examen) se apunta en su `Main sources.md` / `calendar.md` con `fuente: Grok Bot <nombre>, <fecha>`. Si choca con lo que ya hay, enséñame las dos versiones y pregunta.
- No repitas lo que ya hace un Bot (p. ej. avisarme de algo que el Bot ya me mandó).

## Fuentes y herramientas
- **Moodle:** primero la skill moodle (API, sin navegador). Las descargas caen en `_moodle/inbox/` hasta archivarlas; nunca sobrescribir. El navegador (Claude in Chrome, sin capturas) solo para lo que la API no da o para renovar el token.
- **Guías docentes (públicas):** <URL o patrón de URL de las guías docentes de <UNI>>. Enlace en el `Main sources.md` de cada asignatura.
- **Wuolah:** reglas en `<LAB>/kit/guias/uni.md` (solo páginas de <UNI>, nunca gastar monedas, lista primero y descargar solo lo que apruebe).
- **Leer PDFs:** renderiza la página a PNG con PyMuPDF (`pymupdf.open(f)[i].get_pixmap(dpi=100).save(png)`) y lee la imagen. **Apuntes manuscritos del profe:** transcríbelos una vez a `.md` (Markdown + LaTeX, marcas `<!-- p. N -->`, `(?)` en lo dudoso) en `Study notes (Claude)/_source/transcripts/` y lee la transcripción en vez del PDF; renderiza solo figuras o puntos `(?)`.
- `.ppt`/`.docx` antiguos del profe → PDF con Office (COM) para poder leerlos.
- (Solo Windows) Consola en cp1252: Python con `PYTHONIOENCODING=utf-8` al imprimir texto con fórmulas.

## Calendario
<!-- Deja solo la línea que toque: la primera si instaló la fase 6 (email y calendario), la segunda si no. -->
- Reglas en el CLAUDE.md global. Un calendario por asignatura + General; igual que el `calendar.md` de cada asignatura.
- Aún sin herramienta de calendario: las fechas van solo en el `calendar.md` de cada asignatura.
