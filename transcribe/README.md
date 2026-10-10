# transcribe: transcribir audios en local (0 tokens)

Claude no puede escuchar audio. `transcribe.py` usa Whisper (faster-whisper) en tu PC: gratis, sin tokens, nada sale del ordenador. Sirve para audios de WhatsApp (`.ogg`, `.opus`), `.m4a`, `.mp3`… y también vídeos `.mp4` (saca el audio solo, **no hace falta ffmpeg**).

## Instalación (una vez)
Windows:
```
python -m venv "%USERPROFILE%\.whisper"
"%USERPROFILE%\.whisper\Scripts\python.exe" -m pip install faster-whisper av numpy
```
Mac / Linux:
```
python3 -m venv ~/.whisper
~/.whisper/bin/python -m pip install faster-whisper av numpy
```
- Venv en una ruta corta a propósito: en Windows, dentro de carpetas con rutas largas pip falla por el límite de 260 caracteres. En Linux va en un venv también porque en muchas distribuciones `pip install` global está bloqueado (`EXTERNALLY-MANAGED`).
- El modelo se descarga solo la primera vez a `~/.cache/huggingface` (`large-v3-turbo` ≈ 1,5 GB; `small` ≈ 0,5 GB).
- El python del venv es `WHISPER_PY` en `kit-datos.yaml`: Windows `<HOME>/.whisper/Scripts/python.exe`, Mac/Linux `<HOME>/.whisper/bin/python`.

## Uso
```
"<WHISPER_PY>" -I transcribe.py "<audio>" "<palabras pista: nombres, jerga>" [--model small] [--lang es]
```
Imprime el texto en una sola tirada (sin marcas de tiempo ni quién habla). Para ficheros largos, que Claude lo lance en segundo plano y lo guarde en un `.txt`.

## Lo que se midió (CPU i7 de portátil, español)
- Audio de 36 s: autotranscripción de WhatsApp muy mala (~31 % de palabras mal); `small` 8 s (~20 %); `large-v3-turbo` 32 s (~16–18 %, el sentido nunca cambia). Por defecto: turbo + pistas.
- Vídeo de 104 min: turbo tardó ≈ **0,8× la duración** (unos 80 min). `small` ≈ 3× más rápido con más errores.
- **Punto débil: nombres propios y términos técnicos** (≈ 30 errores en 15 000 palabras: apellidos, siglas, palabras en inglés). La pista solo arregla las palabras que pones en ella. Un email dictado salió mal: **nunca te fíes de un email o apellido sacado de una transcripción**; compruébalo con las diapositivas o la web.
- Trucos: mete en la pista los nombres de quien habla y la jerga (las diapositivas son buena fuente); corrige después con una lista de reemplazos.

No se hizo un MCP para esto: el modelo sería el mismo y añadiría herramientas a cada sesión.
