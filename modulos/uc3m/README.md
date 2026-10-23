# Módulo `uc3m` — Universidad Carlos III de Madrid

Se ofrece si en la fase 0 la universidad es la UC3M. No instala nada propio: **preconfigura el módulo `moodle`** (Aula Global) y añade lo que se sabe de la UC3M. Solo datos públicos; nada de nadie.

## Aula Global = Moodle (módulo `moodle`)
- `moodle.json`: `"site": "https://aulaglobal.uc3m.es"`, `"token_file": "~/.moodle-token"`, `courses` vacío → `moodle.py courses` lista las asignaturas en las que está matriculada la persona con su id (`[2026/27] C2.<grado>.<asignatura>-<grupo>`); cada una con el nombre corto que elija (= nombre de su carpeta).
- **Token:** la UC3M entra por **SSO** (Aula Global redirige a `login.uc3m.es`, CAS; según la cuenta puede pasar después por la cuenta de Google de la uni, `<NIA>@alumnos.uc3m.es`), así que `login/token.php` con usuario y contraseña **no sirve**. Se saca con `launch.php` desde el navegador ya logueado (pasos en `modulos/moodle/SKILL.md`, caso SSO). Si Aula Global dice que no hay sesión, la persona entra ella; si pide contraseña, código o un consentimiento nuevo, lo hace la persona (Claude nunca escribe credenciales).
- **Windows, primer uso:** si `moodle.py` dice `SSL: … CERTIFICATE_VERIFY_FAILED`, falta en Windows la raíz de la cadena de Aula Global (*Hellenic Academic and Research Institutions ECC RootCA 2015*, visto el 2026-10-21); el propio mensaje dice cómo traerla (una petición con `Invoke-WebRequest`).
- **Fuera de la uni, VPN:** desde el 2026-10-22 (fallo de seguridad de PHP) Aula Global solo deja entrar desde la red de la UC3M o con su VPN (**GlobalProtect**, portal `myvpn.uc3m.es`, con verificación en dos pasos; descarga en `uc3m.es/sdic/servicios/vpn`). Sin ella, todo da `HTTP 403` con un «Aviso de Seguridad», también el login: `moodle.py` lo dice. **Que se conecte sola (Windows):** con GlobalProtect instalado y el portal puesto una vez a mano, copia `modulos/moodle/vpn-globalprotect.ps1.txt` → `~/.claude/skills/moodle/vpn-globalprotect.ps1` y en `moodle.json` `"vpn": "powershell -NoProfile -ExecutionPolicy Bypass -File \"<HOME>/.claude/skills/moodle/vpn-globalprotect.ps1\" -Site https://aulaglobal.uc3m.es"`. Ante un 403, `moodle.py` pulsa *Connect* en GlobalProtect (su panel sale abajo a la derecha; ni ratón ni teclado) y el login de la UC3M (SSO con la cuenta de Google de la uni) se completa solo en el navegador si ya tiene la sesión: unos 15 s. Probado el 2026-10-23. Si el login pide algo (contraseña, segundo paso), lo hace la persona; el script no escribe nunca. Puede que la ventana del login quede delante unos segundos, hasta que el script la cierra.
- Si la persona prefiere llamarlo `aula >` en vez de `moodle >`: cambia `moodle >` por `aula >` en la `description` y los títulos del SKILL.md instalado (el `name:` puede quedarse).
- Cursos de años anteriores: existen, pero sin matrícula no se ven.

## Guías docentes (públicas)
`https://aplicaciones.uc3m.es/cpa/generaFicha?est=<código del grado>&asig=<código de la asignatura>&idioma=<2 en | 1 es>&anio=<año de inicio del curso>`. Los dos códigos salen del nombre del curso en Aula Global (`C2.<grado>.<asignatura>-<grupo>`). El enlace va en el `Main sources.md` de cada asignatura (módulo `asignaturas`).

## Calendario oficial de exámenes
Se publica por grado al empezar el curso y **manda sobre la fecha que diga la guía docente** (han llegado a no coincidir). Apuntarlo en `calendar.md` / `Main sources.md` como `sure (calendario oficial, <fecha>)`.

## Wuolah
Reglas generales en `kit/guias/uni.md`. En la UC3M: solo páginas **de la UC3M**; cada grado es una *community* (`?communityId=…` en la URL), p. ej. Ingeniería Física 85727 · Doble grado Ing. Física + Tecnologías Industriales 97620 · Grado en Ciencias 97618. Buscar la asignatura en español y en inglés y mirar los otros grados de la UC3M que la compartan.

## Al instalar
1. Instala el módulo `moodle` con estos valores (fase 3 de `kit/CLAUDE.md`). En Windows, ofrécele la VPN automática de arriba (`vpn-globalprotect.ps1`; apúntala en `instalado:`).
2. En `kit-datos.yaml`: `UNI: UC3M`, `MOODLE_URL: https://aulaglobal.uc3m.es`, y `modulos:` + `uc3m`.
3. Si instala también `asignaturas`: en `CLAUDE.curso.md`, la línea *Guías docentes* con el patrón de arriba.
