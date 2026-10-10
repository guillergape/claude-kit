# Google Calendar con Claude

## Herramienta
- **Conector de Google Calendar de claude.ai** (Ajustes de claude.ai → Conectores; si tu plan los tiene). Cero instalación, no caduca. Ojo: devuelve las horas en UTC (`…Z`): convertir a Europe/Madrid antes de mover o decir una hora. Pasar siempre `notificationLevel: NONE` (por defecto avisa a los invitados). Recordatorios en `overrideReminders`.
- **MCP `google-workspace`** (taylorwilsdon/google_workspace_mcp, `uvx workspace-mcp`): sirve también para Gmail, Docs y Drive, y para **crear calendarios nuevos** (`create_calendar`). Necesita un cliente OAuth propio en Google Cloud; en modo Testing los tokens **caducan cada 7 días** (la primera llamada da el enlace para reautorizar). Ver `email.md`.
- Si se sincroniza el calendario de Google en el móvil (Samsung Calendar, iOS…), lo que añade Claude aparece allí.

## Reglas básicas que me funcionan (las del autor del kit, sin sus colores)
- **Un calendario por asignatura** (nombre corto: `Prog`, `Calculo`…), para poder mostrar/ocultar cada una. Lo que no es de una asignatura (charlas, sesiones informativas, eventos) va en un calendario **General**.
- **Clases:** eventos semanales recurrentes a su hora real, con el aula como ubicación. Saltar festivos y días sin clase.
- **Todo lo que tiene hora va a su hora**, nunca de día completo. De día completo solo si la hora es de verdad desconocida. (Un evento de día completo no se puede pasar a horario con un update: borrar y crear otra vez.)
- **Clases canceladas:** a su hora real (no de día completo) y quitarlas ese día de la clase recurrente.
- **Marcas de duda en el título:** dudoso/probable → `¿…?`; muy dudoso → `¿¿…??`. En la descripción, la fuente y por qué hay duda.
- **Grupos de prácticas aún desconocidos:** meter todas las opciones posibles con `¿¿…??` y borrar las que no son cuando salgan los grupos.
- **Recordatorios en lo importante** (prácticas, exámenes, charlas, reuniones, asistencia obligatoria; también los `¿…?`): solo **popup**, nunca email: **2 h antes** (`120`) y **la víspera a las 21:00** (minutos = `180 + hora·60 + min` del inicio; p. ej. 17:15 → 1215, 12:30 → 930). Días completos: solo la víspera (`180`). Si la hora duda entre dos franjas, un aviso de 2 h para cada una. Clases semanales y plazos de entrega: sin avisos extra. Recalcular si cambia la hora.
- **Plazos de entrega** a su hora (p. ej. 23:30–23:59 para una entrega a las 23:59).
- **Nunca enviar invitaciones ni notificaciones** a nadie.
- Antes de crear, buscar si ya existe (evitar duplicados).

## Lo que tiene que preguntarte tu Claude (y apuntar en tu CLAUDE.md global)
- ¿Colores por tipo? (el autor del kit usa: prácticas verde, exámenes rojo con los finales en MAYÚSCULAS, canceladas gris, clases amarillo; tú decides.)
- ¿Qué recordatorios y a qué horas? ¿Calendario General sí/no?
- ¿Qué cuenta de Google (personal / universidad)? Cuál es la de por defecto.
- ¿Qué hacer con una entrega ya hecha? (el autor del kit: la pone gris, la mueve a un calendario `old` y apunta en la descripción quién la entregó, cuándo y dónde.)
