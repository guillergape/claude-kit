# Informe de instalación del kit — <Nombre>

<!-- Se copia a <LAB>/INFORME_MIGRACION.md en la fase 0 y lo va rellenando Claude DURANTE la instalación (al terminar
     cada fase), así sirve también para retomar tras un /clear. Al final la persona se lo manda a quien le pasó el kit
     respondiendo a su correo. Después sigue vivo: "Uso de cada componente" y "Actualizaciones" se van rellenando. -->

## Sistema
- Versión del kit (copia la línea de `kit/VERSION.txt`): 
- Cómo llegó el kit (git / zip): 
- Fecha de inicio: 
- SO (y distribución / escritorio en Linux) / shell / Python (`PY`): 
- Claude Code (versión), plan (Pro/Max/API), modelo y esfuerzo usados: 
- Carpeta del lab: 
- Carpeta de la uni (y si está en Google Drive): 
- Conectores de claude.ai disponibles (Gmail / Calendar / Drive) y con qué cuenta: 
- Claude in Chrome instalado / navegadores: 
- Módulos elegidos (`modulos:` de `kit-datos.yaml`): 

## Estado por fase
| Fase | Estado (✅ hecho · ⏭ saltado · ❌ falló · ⏳ a medias) | Notas |
|---|---|---|
| 0 Reconocimiento, preguntas, `kit-datos.yaml` | | |
| 1 Reglas globales | | |
| 2 Status line + costlog/blocklog + modo carpeta | | |
| 3 Skills (md2pdf, commands, progress, módulo moodle) | | |
| 4 keep-awake | | |
| 5 Transcripción | | |
| 6 Email + calendario | | |
| 7 Uni (módulos asignaturas / uc3m / grok-bot, Wuolah) | | |
| 8 Extras (old.py, timelog, leftover, Instinct, Overleaf) | | |
| 9 Cierre | | |

## Qué se instaló
<!-- componente → dónde quedó instalado → cómo se probó (lo mismo, en corto, está en `instalado:` de kit-datos.yaml) -->

## Qué NO se instaló y por qué
<!-- p. ej. "send.py: no uso el MCP de Google" / "keep-awake: tengo Mac" -->

## Qué falló o tuvo bugs (para que el autor lo arregle en el kit)
<!-- componente · SO · qué pasó · error EXACTO · cómo se arregló (o "sin resolver" / "pendiente: chat X") · si se cambió el código, el cambio -->

## Cambios hechos fuera de la carpeta del lab
<!-- Una fila por cambio, también lo que no son ficheros (pip, venv, paquetes del sistema, MCP, proyecto de Google Cloud). La usan `desinstalar kit >` y `actualiza kit >`. -->
| Componente | Fichero / carpeta / instalación | Qué se añadió exactamente | .bak- | .kit- | Fecha |
|---|---|---|---|---|---|

## Chats aparte
<!-- Fallos o procesos grandes que no se resolvieron aquí (regla 10 de la guía). Para cada uno: título · modelo y esfuerzo recomendados · mensaje exacto para pegar (autocontenido). -->

## Ideas / peticiones para el autor del kit

## Actualizaciones
<!-- Una entrada por `actualiza kit >` (ACTUALIZAR.md): fecha · versión vieja → nueva · qué se aplicó · qué se fusionó · qué no y por qué · fallos. -->

## Uso de cada componente
<!-- La actualiza Claude (regla "Herramientas del kit" del CLAUDE.md global). costlog> y blocklog> se cuentan por las filas de costlog.csv / blocklog.csv; send> no queda contado. Reenvía este informe al autor del kit cuando lo pida. -->
| Componente | Usos | Recordatorios | Último uso |
|---|---|---|---|
