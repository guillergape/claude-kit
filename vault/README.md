# Vault — contraseñas y tokens que Claude usa sin verlos

Tus scripts leen sus tokens y claves de API del almacén de credenciales del sistema en vez de un fichero de texto. Claude solo ve nombres, usuarios y URLs; ningún comando imprime una contraseña.

- **Dónde:** el almacén del sistema a través de `keyring`, servicio `claude-vault`: **Windows** Administrador de credenciales (DPAPI, ligado a tu sesión de Windows; se ve en *Credential Manager → Windows Credentials*), **Mac** Llavero, **Linux** Secret Service (GNOME Keyring / KWallet). Nunca en un fichero, en la nube ni en git.
- **Instalar:** `<PY> -m pip install keyring` (tkinter para las ventanas, ver *Por sistema operativo* en `kit/CLAUDE.md`). Copia `kit/vault/` → `<LAB>/vault/`. Prueba: `<PY> <LAB>/vault/vault.py --test` → `ok vault (…)` (usa un servicio aparte, `claude-vault-test`, y lo borra: no toca tus entradas).
- **Script:** `<PY> "<LAB>/vault/vault.py" <comando>`.

| Comando | Qué hace |
|---|---|
| `add <nombre> [--user U] [--url URL]` | Ventana donde **tú** escribes la contraseña (oculta); Claude solo recibe «stored». |
| `new <nombre> --user U [--url URL]` | Genera una contraseña de 20 caracteres, la guarda y la pone en el portapapeles (para registrarte en una web). |
| `copy <nombre>` | Contraseña al portapapeles 30 s y luego se borra; en Windows, marcada para que no entre en el historial de Win+V ni en el portapapeles en la nube. |
| `user <nombre>` / `list` / `rm <nombre>` | Usuario / nombres + usuarios + URLs / borrar. |
| `open` | **Tu** ventana: cada entrada con Show / Copy / Delete, y Add / Generate. Se abre con **`vault>`** en cualquier chat (0 tokens, hook de `costlog.py`, si `vault/` está en `<LAB>/vault/`). |

**Desde scripts de Python:** `sys.path.insert(0, "<LAB>/vault"); from vault import get; tok = get("mi-api")` (nunca lo imprimas ni lo apuntes en un log). Para pasar un token de un fichero al vault: `vault.py add <nombre>` (lo pegas tú en la ventana) y luego borra el fichero a la papelera.

## Qué puede y qué no puede hacer Claude con él
- **No:** pegar una contraseña del vault en un formulario de inicio de sesión o de registro, ni crear cuentas. Sus reglas de seguridad le prohíben meter contraseñas y crear cuentas, y que vea el valor o no da igual.
- **Sí:** tokens y claves de API de **tus propios scripts** (`get()` en vez de ficheros con el token en claro), y que tú uses `copy` o la ventana.
- **Inicios de sesión en el navegador:** como siempre, el gestor de contraseñas del navegador rellena los campos y Claude solo pulsa «Entrar».
- Regla para el CLAUDE.md global: sección `kit:vault` de `plantillas/CLAUDE.global.md`.

## Límites
- Evita que un secreto salga **por accidente** (transcripts, logs, capturas), no una lectura deliberada: Claude corre con tu usuario. Por eso la regla es que nunca imprima, devuelva ni lea un secreto, tampoco del portapapeles.
- Probado en Windows 11: `get()` lo usan los scripts del autor del kit desde el 26 oct 2026, y él probó los botones de la ventana y `vault>` el 30 oct. **Mac/Linux sin probar:** `keyring` funciona ahí, pero el portapapeles va por `pbcopy` / `wl-copy` / `xclip` y en esos sistemas no se excluye del historial del portapapeles. Si algo falla, apúntalo en el informe.
