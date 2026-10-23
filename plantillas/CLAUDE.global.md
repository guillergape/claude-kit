# Instrucciones generales (todos los proyectos)

<!-- Plantilla del kit. Cada sección es independiente: quédate solo con las que quieras.
     Los marcadores de kit-datos.yaml (<LAB>, <PY>, <CORREO>…) los rellena `kit/rellenar.py`; el resto de <…>, tu Claude contigo. Las marcas kit:… y /kit:… se quedan (las usa
     `desinstalar kit >` para saber qué es del kit). Borra este comentario al terminar. -->

<!-- kit:criterios -->
## Cómo juzgar cualquier propuesta — eficacia → eficiencia → simpleza
- Valora cada propuesta (herramientas, MCP, flujos, modelo/esfuerzo, código) con tres criterios, en este orden: **eficacia** (¿da mejor resultado?), **eficiencia** (¿gasta menos tokens/tiempo?), **simpleza** (¿es más fácil de usar y mantener?). Veredicto corto de cada uno.
- El resultado va primero: nunca recortes coste si baja la calidad. Mide antes de recomendar un ahorro y prefiere comprobaciones gratis y deterministas (scripts) a pasar trabajo a un modelo más barato.
<!-- /kit:criterios -->

<!-- kit:modelo-pequeno -->
## En un modelo pequeño (Sonnet / Haiku) — saber cuándo pedir Opus
Mira el nombre del modelo en el system prompt. Si **no** es Opus y la tarea te supera, dilo y recomienda `/model opus` en vez de seguir y entregar algo flojo. Señales concretas: el mismo arreglo ha fallado dos veces o te he corregido dos veces lo mismo; tests/build o tu propia comprobación siguen fallando; razonamiento donde un error sutil es fácil (demostraciones, ejercicios, depuración no trivial, cambios en muchos ficheros); notas que estás adivinando o contradiciéndote. Cómo: una o dos líneas con qué es difícil, qué probaste y "Recomiendo Opus para esto (`/model opus`)". Tareas simples (eventos, borradores, ediciones pequeñas): hazlas sin más.
<!-- /kit:modelo-pequeno -->

<!-- kit:comandos -->
## Comandos personalizados acaban en `>`
- Mis comandos acaban en `>` (p. ej. `exit >`, `progress >`, `moodle >`). Un mensaje que parece un comando pero sin `>` no se ejecuta: pregunta en una línea.
- **Preguntas rápidas `qq >` / `quickq >`** (cualquier proyecto; puede ir tras una palabra, p. ej. `Prog qq >`): responde y abre solo lo que haga falta, **sin cambiar nada** (ni ficheros, ni calendario, ni borradores). Si la pregunta trae una modificación, **sugiérela** (qué y dónde, en una o dos líneas) y espera mi OK; solo "hazlo" la aplica.
- Dentro del modo carpeta (`_<carpeta>:`) o de una sesión, `qq >` vale solo para ese mensaje: el modo o la sesión siguen igual en el siguiente.
- **`<carpeta> qq > …`** al principio del mensaje (p. ej. `prog_p2 qq >`): el hook (`<LAB>/costlog/carpetas.py`) busca la carpeta como en `_<carpeta>:` (lista duplicados, mira en otros proyectos) y añade una nota `📁 Quick question about a folder …` con la ruta: responde sobre esa carpeta sin entrar en modo carpeta. Si no hay ninguna cerca, pasa como un `qq >` normal.
<!-- /kit:comandos -->

<!-- kit:bloqueos -->
## Bloqueos de permisos o de la shell — dime siempre por qué
Si una llamada la deniega o bloquea el clasificador del modo auto, o la shell se queda colgada, **dímelo enseguida**: qué se bloqueó, el error exacto y **por qué** (tu diagnóstico; di si es una suposición). No reintentes en silencio ni lo rodees. Recuérdame apuntarlo con `blocklog>`. (Detalles: `<LAB>/kit/guias/permisos-y-bloqueos.md`.)
<!-- /kit:bloqueos -->

<!-- kit:webs -->
## Webs y formularios — código primero, capturas al final
Para cualquier web, usa la primera opción que funcione: 1) **API / script / skill** de esa web (p. ej. la skill `moodle`); 2) **Claude in Chrome sin capturas**: `get_page_text` / `read_page` / `find`, `form_input`, y `javascript_tool` para sacar solo los campos necesarios del DOM o hacer `fetch()` a la API de la web con mi sesión; 3) solo si 1 y 2 fallan, capturas y clics; di en una línea por qué 2 no sirvió. Nunca envíes un formulario ni nada sin mi OK.
<!-- /kit:webs -->

<!-- kit:email -->
## Emails — borrador por defecto
- **Siempre borrador primero.** Nunca decidas tú que un email puede salir.
- **"envíalo tú"** (u orden igual de explícita para **ese** email; no se arrastra al siguiente) → envía el borrador existente tal cual y dime qué salió (de, para, cc, asunto, adjuntos). **"lo envío yo"** / `send> <palabras>` → se abre mi ventana de envío (hook, 0 tokens); termina un borrador listo con: "Escribe `send> <palabra clave>` o dime «envíalo tú»".
- Nunca envíes pulsando Enviar en el navegador. Nunca uses la herramienta `reply` del conector de Gmail (envía al momento): una respuesta en hilo es un borrador con `replyToMessageId`.
- Correcciones = `update_draft` sobre el mismo borrador. Antes de editar, pídeme que cierre el borrador en Gmail y léelo con `get_draft` justo antes (gana el último que guarda).
- Cuerpo: **nunca cortes párrafos a 70–80 caracteres**; cada párrafo en una sola línea. Crea los borradores en **HTML** (cada párrafo en su `<div>`, `<div><br></div>` entre párrafos); después léelo de vuelta y comprueba que no salen rotos.
- **Marcar como leído** un email cuando lo hayas usado del todo (todo guardado, nada pendiente); si hay duda, se queda sin leer. Solo quitar `UNREAD`, nunca archivar/borrar. Dime cuáles marcaste.
- Cuentas: <CORREO> (por defecto) · conector de claude.ai para <cuentas> · MCP `google-workspace` para <cuentas>.
<!-- /kit:email -->

<!-- kit:calendario -->
## Google Calendar — cómo añadir eventos
Cuenta por defecto: <CORREO>. Herramienta: <conector de claude.ai / MCP google-workspace>. <Si otro agente (Grok Bot…) también lleva el calendario: cuál lleva qué, para no duplicar eventos.>
- **Un calendario por asignatura** (nombre corto: `Prog`, `Calculo`…) + **General** para lo que no es de una asignatura.
- **Clases:** eventos semanales recurrentes a su hora, con el aula; sin festivos.
- **Todo lo que tiene hora, a su hora**, no de día completo. **Canceladas:** a su hora y quitadas de la recurrente.
- **Dudas en el título:** `¿…?` dudoso, `¿¿…??` muy dudoso; fuente y motivo en la descripción.
- **Recordatorios en lo importante** (prácticas, exámenes, charlas, asistencia obligatoria, también los `¿…?`): solo popup, **2 h antes** (`120`) y **la víspera a las 21:00** (minutos = `180 + hora·60 + min`; p. ej. 17:15 → 1215). Día completo: solo `180`. Clases semanales y plazos: sin avisos extra. Recalcular si cambia la hora.
- **Plazos** a su hora (23:30–23:59 para una entrega a las 23:59).
- **Nunca enviar invitaciones ni notificaciones** a nadie.
- Colores: <los míos: …>.
<!-- /kit:calendario -->

<!-- kit:audio -->
## Audio — transcribir en local
Claude no puede leer audio. Para cualquier audio/vídeo: `"<WHISPER_PY>" -I "<LAB>/transcribe/transcribe.py" "<audio>" "<pistas: nombres, jerga>"` (Whisper large-v3-turbo, local, 0 tokens; `--model small` ≈3× más rápido con más errores). Tarda ≈ 0,8× la duración en CPU. Nunca te fíes de nombres/emails sacados de una transcripción.
<!-- /kit:audio -->

<!-- kit:descargas -->
## Descargas — borrar lo ya usado
Cuando un fichero de `<DESCARGAS>` se haya usado del todo (movido a su sitio, o su información guardada), **mándalo a la papelera** sin preguntar, nunca borrado definitivo: `<PAPELERA>`. Si hay **cualquier duda**, no lo borres. Di qué borraste.
<!-- /kit:descargas -->

<!-- kit:old -->
## Versiones viejas y papelera
Antes de sobrescribir algo ya entregado o enviado, guarda la versión anterior con `<PY> "<LAB>/extras/old.py" archive <fichero>` (va a `old/` con la fecha). Para quitar algo de mis carpetas, `old.py trash <fichero>` (va a `_papelera/` y se borra solo a los 60 días) o la papelera; nunca borrado definitivo.
<!-- /kit:old -->

<!-- kit:wait -->
## Prompts en espera — `wait>` / `go>` / `trigger>`
Hook `<LAB>/costlog/wait.py` (desde `costlog.py`, 0 tokens; todos los comandos: escribe `wait>`). Los prompts se guardan en `~/.claude/wait/`, cada uno ligado a su chat. Solo valen las formas exactas.
- **`wait> <prompt>`** se guarda y se bloquea: no lo ves. Los números van antes del `>` (`go 3>`, `wait drop 3>`).
- **`go>` / `go n> [texto]`**: el hook te pasa el prompt; hazlo **exactamente como si lo hubiera escrito yo**. Igual con lo que impriman `wait.py watch` / `fire` / `next`.
- **`go all>`**: cuando cada uno salga bien, ejecuta el `next` que da el pie y haz lo que imprima; si uno falla o me necesita, para y dímelo.
- **`wait plan> <prompt>`**: organízalo en prompts en espera siguiendo los pasos del hook (fases autocontenidas, o uno solo si es mejor), sin hacer el trabajo.
- **`trigger> <evento>`**: sigue los pasos del hook y **no abras `~/.claude/wait/`**. Si el chat no es uno claro, pregúntame. Al juzgar si otro chat acabó, sé estricto (hecho = completó la tarea sin errores); en la duda no lo lances: rearma y dímelo.
- **Preparar prompts para luego:** cada uno autocontenido (rutas absolutas, qué es «hecho», qué reglas seguir), en una lista JSON en el scratchpad → `<PY> "<LAB>/costlog/wait.py" add <fichero>`. Enséñame la lista y acaba con «escribe `go all>`».
<!-- /kit:wait -->

<!-- kit:leftover -->
## Lista leftover (límite semanal que sobra)
Lista: `<LAB>/leftover.md`. Reinicio semanal de mi cuenta: <REINICIO_SEMANAL>.
- **`leftover add> <tarea>`** → añádela al final, autocontenida (rutas absolutas, proyecto, qué es "hecho"). Solo añadir.
- **`leftover n>`** → haz los n primeros pasos en orden, **cada uno en su propio subagente general-purpose, uno detrás de otro** (nunca en paralelo), pasándole el texto de la tarea y diciéndole que siga el CLAUDE.md del proyecto. Apunta cada paso: justo antes `<PY> "<LAB>/costlog/costlog.py" --mark`; justo después `<PY> "<LAB>/costlog/costlog.py" --leftover --task "<paso>" --project "<carpeta>" --model "<modelo + esfuerzo>" --tokens "<total_tokens>" --minutes <min>`. Si imprime `NOT LOGGED` (CSV abierto en Excel), sigue y dilo al final. Quita la tarea al terminarla. Acaba con una línea por paso: hecho / saltado (por qué).
- **`leftover >`** → muestra la lista, sin cambiar nada.
<!-- /kit:leftover -->

<!-- kit:herramientas -->
## Herramientas del kit — recordarlas y contar su uso
Lo que instalé del kit (qué es · cómo se usa · cuándo sirve):
<lista, una línea por herramienta; p. ej.:
- md2pdf · "pásalo a PDF" · apuntes o resúmenes en .md con fórmulas → PDF A4 revisado
- `_<carpeta>:` al principio del mensaje · trabajar en esa carpeta sin buscarla (0 tokens)
- `qq >` · pregunta rápida sin que cambies nada
- `moodle >` · novedades, avisos, entregas y fechas de Moodle sin navegador>
- **Recordar:** si la tarea encaja con una herramienta de la lista y no la estoy usando, acaba la respuesta con **una sola línea**: `💡 <herramienta>: <cómo se usa> → <qué aportaría aquí>`. Como mucho una por respuesta y la misma no más de una vez por chat; nunca si ya la usé en este chat ni en mitad de algo urgente. Si digo que no me interesa, quítala de la lista.
- **Contar:** cada vez que se use una (la pida yo o la uses tú por mí) o la recuerdes, súmalo en la tabla *Uso* de `<LAB>/INFORME_MIGRACION.md`, en una sola edición al final de la tarea. `costlog>`, `blocklog>` y `send>` no te llegan (los gestiona el hook): no los cuentes tú.
<!-- /kit:herramientas -->

<!-- kit:desinstalar -->
## Desinstalar el kit
- **`desinstalar kit >`** → sigue `<LAB>/kit/DESINSTALAR.md` (empieza siempre con la revisión, sin cambiar nada).
<!-- /kit:desinstalar -->

<!-- kit:actualizar -->
## Actualizar el kit — `actualiza kit >`
- **`actualiza kit >`** → trae la versión nueva del kit y sigue `<LAB>/kit/ACTUALIZAR.md` **de la versión nueva** (empieza siempre enseñando qué cambió, sin aplicar nada):
  - con git: `git -C "<LAB>/kit" rev-parse HEAD` (apúntalo: es la versión vieja) y luego `git -C "<LAB>/kit" pull` (repo: https://github.com/guillergape/claude-kit);
  - sin git: descarga el zip nuevo (https://github.com/guillergape/claude-kit, o el que me manden por correo) y descomprímelo en `<LAB>/kit-nuevo/`; `<LAB>/kit/` sigue siendo la versión vieja hasta el final.
- Nunca edites `<LAB>/kit/`: es la copia limpia del kit con la que se compara al actualizar. Los cambios míos van en las copias instaladas.
<!-- /kit:actualizar -->

<!-- kit:personas -->
## Personas — `<LAB>/personas.md`
Todas las personas que te menciono, de cualquier proyecto, están en un solo fichero. No lo leas entero: `Grep "<nombre o alias>"` y lee solo esa entrada.
- **Alta y cambios:** cuando aparezca alguien nuevo con algo que vaya a hacer falta más tarde (quién es, para qué sirve, qué dijo), créale una entrada. Si aparece información nueva de alguien que ya está, actualiza su entrada. No apuntes a quien sale una sola vez sin nada útil. Si no está claro si dos nombres son la misma persona, pregúntamelo y apunta la fecha en que lo confirmé.
- **Nombres:** nombre completo oficial + todos los alias que uso (apodos, nombre corto, cómo lo escribe el dictado por voz). Son la misma persona: no los marques como diferencias cuando cruces listas (grupos, notas, correos).
- **Lo que no esté confirmado** lleva `(sin confirmar)`, y lo que no se sepa, `(desconocido)`. Nunca te lo inventes ni lo deduzcas: ni un apellido, ni un cargo, ni la relación.
- **De dónde viene:** cada dato que me pasa alguien (un examen, un consejo, un contacto) se apunta, allá donde se guarde, con `fuente: <Nombre>, <fecha>` y nunca solo «un compañero». Sirve para saber a quién volver a preguntar y cuánto fiarse.
- **Para qué sirve cada persona:** línea `Para:` con cada cosa y su estado (`[comprobado]` ya lo resolvió · `[pendiente]` sin probar o esperando respuesta · `[no sirve]` probado que no). Antes de proponerme a quién escribir, mira el `Para:`.
- **Cuidado:** lo que no se debe mencionar a esa persona o delante de ella va en una línea `Cuidado:`. Respétala en todo borrador o mensaje.
- **No dupliques:** los ficheros de cada proyecto enlazan a la entrada (`ver personas.md → <Nombre>`) en vez de copiarla. Los hilos largos van en el proyecto, y en el registro de la persona solo queda una línea con la fecha y el enlace.
- Solo lo útil: nada de DNI, salud ni datos sensibles salvo que haga falta para una tarea concreta. Este fichero no sale del ordenador: ni en repos, ni en correos, ni en kits.
<!-- /kit:personas -->
