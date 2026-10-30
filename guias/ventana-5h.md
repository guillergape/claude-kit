# Empezar la ventana de 5 h a una hora fija (rutina en la nube, con el ordenador apagado)

El límite de uso de 5 h empieza a contar con el primer mensaje. Si el primer mensaje del día es a las 07:00, la ventana se reinicia a las 12:00, a las 17:00… y encaja con tu horario de estudio o trabajo. Una **rutina en la nube** manda ese primer mensaje por ti aunque el ordenador esté apagado. Cuesta casi nada: una respuesta de una palabra con el modelo más pequeño.

## Cuándo ofrecerlo
Solo si la persona lo quiere, y tiene un plan con rutinas (la skill `schedule` / `/schedule` existe en su Claude Code). Pregúntale: **a qué hora** quiere que empiece la ventana, **qué días** (todos o solo entre semana) y **su zona horaria**.

## Cómo (Claude lo hace con la skill `schedule`, herramienta `RemoteTrigger`)
1. `RemoteTrigger list` para ver qué rutinas tiene ya (no toques las que no sean tuyas) y la skill `schedule` para sacar el `environment_id` de su cuenta.
2. Las rutinas se programan en **UTC** y no entienden el cambio de hora, así que se crean **dos**, una de invierno y otra de verano, cada una limitada a sus meses (`hora UTC = hora local − desfase`). Ejemplo para las 07:00 de Madrid, todos los días: invierno `0 6 * 1-3,11-12 *` y verano `0 5 * 4-10 *`. Para solo entre semana, `1-5` en el último campo. Calcula tú las horas para su zona y confírmaselas («07:00 Madrid = 06:00 UTC en invierno»).
3. Cuerpo de `create` (cambia `name`, `cron_expression`, `environment_id`, y un `uuid` v4 en minúsculas nuevo para cada rutina):
```json
{"name": "OK 7:00 (invierno)", "cron_expression": "0 6 * 1-3,11-12 *", "enabled": true,
 "job_config": {"ccr": {"environment_id": "<ENV>",
  "session_context": {"model": "claude-haiku-5-5", "allowed_tools": ["Read"]},
  "events": [{"data": {"uuid": "<uuid v4>", "session_id": "", "type": "user", "parent_tool_use_id": null,
   "message": {"content": "Reply only with: OK", "role": "user"}}}]}}}
```
   Sin `sources` (no hace falta repositorio). Modelo: el Haiku más reciente que le salga en `/model`.
4. Dile lo que ha creado (nombre, cron y hora local) y el enlace `https://claude.ai/code/routines`. Para borrarlas, solo desde esa web (Claude no puede borrar rutinas).

## Lo que hay que saber (visto el 29 oct al crear dos rutinas así en una cuenta del autor)
- La creación funciona sin `sources` y con solo `Read`; `update` con un `cron_expression` nuevo cambia los días sin recrearlas.
- **El esfuerzo («low») no se puede poner** en una rutina: el cuerpo solo acepta el modelo. No importa, la respuesta es una palabra.
- **El servidor añade hasta unos minutos de margen**: el `next_run_at` que devolvió salía hasta 6 min después de la hora del cron.
- **Unos días al año sale 1 h antes o después**: el cambio de hora real es el último domingo de marzo y de octubre y las reglas cambian por mes. Para una ventana de 5 h no merece más reglas.
- Las rutinas de la cuenta de **otra persona** no se ven desde la tuya: se crean con la sesión de Claude Code de esa cuenta.
- **Sin comprobar todavía:** que una ejecución real llegue a abrir la ventana de 5 h (se mira en el `/usage` o la barra de estado justo después). Primera comprobación sin esperar a mañana: `RemoteTrigger run` de una de ellas (cuenta como una ejecución real) y mirar en la web que aparece la sesión.
