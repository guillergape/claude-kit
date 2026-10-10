#!/usr/bin/env python3
"""Barrera contra datos personales en el repo (solo stdlib).

    check_privado.py --staged        ficheros staged (hook pre-commit)
    check_privado.py --push          commits que se van a subir (hook pre-push; lee stdin de git)
    check_privado.py --all [carpeta] todos los ficheros de una carpeta (por defecto, la raíz del repo)
    añadir  --patrones RUTA  para probar sin git config

Falla (exit 1) si encuentra:
  a) un correo electrónico que no sea marcador/ejemplo (ejemplo@ejemplo.com, noreply de GitHub...),
  b) una ruta personal (carpeta de usuario de Windows/Linux/Mac, la carpeta de Drive) sin marcador <HOME>/<LAB>,
  c) cualquier patrón de la lista privada, que vive FUERA del repo: su ruta sale de `git config privado.patrones`.
Si no hay ruta, o el fichero no existe o está vacío, BLOQUEA: nunca pasa en silencio.
Del dato privado nunca se imprime el valor: solo fichero, línea y el número de patrón.
"""
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
OK_EMAIL_DOMAINS = {"ejemplo.com", "example.com", "example.org", "example.net", "users.noreply.github.com", "noreply.github.com", "instinct.com", "git.overleaf.com"}
OK_EMAIL_SUFFIXES = (".example", ".invalid", ".test", ".local", ".ejemplo")
OK_EMAIL_LOCALS = {"ejemplo", "example", "tucuenta", "tu_correo", "tucorreo", "correo", "usuario", "nombre", "user", "name", "tu", "noreply"}
PLACEHOLDER = {"user", "usuario", "username", "tu_usuario", "tuusuario", "nombre", "you", "yo", "name", "tu", "foo", "xxx", "...", "ana"}
# C:\Users\<x>, /home/<x>, /Users/<x> (x no empieza por < % $ { y no es un marcador típico)
PATH = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/home/|/Users/)([^\\/\s<>\"'`%${}()\[\]|:*?]+)")
DRIVE = re.compile(r"My[ ]Drive", re.I)


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).lower()


def git(*args, check=True):
    p = subprocess.run(["git", *args], capture_output=True)
    if check and p.returncode:
        sys.exit(f"check_privado: git {' '.join(args)} falló: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout.decode("utf-8", errors="replace")


def load_patterns(override):
    path = override or git("config", "--get", "privado.patrones", check=False).strip()
    if not path:
        sys.exit("BLOQUEADO: git config privado.patrones no está definido (ruta de la lista privada). "
                 "Defínelo: git config privado.patrones \"<ruta>/patrones.txt\"")
    f = Path(path).expanduser()
    if not f.is_file():
        sys.exit(f"BLOQUEADO: no existe la lista privada de patrones ({f}). Sin ella no se pasa nada.")
    pats = []
    for n, raw in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.lower().startswith("re:"):
            pats.append((n, re.compile(fold(s[3:]), re.I)))
        else:
            pats.append((n, fold(s)))
    if not pats:
        sys.exit(f"BLOQUEADO: la lista privada ({f}) no tiene ningún patrón.")
    return pats


def email_ok(addr):
    local, _, dom = addr.lower().rpartition("@")
    return (dom in OK_EMAIL_DOMAINS or dom.endswith(OK_EMAIL_SUFFIXES)
            or local in OK_EMAIL_LOCALS or local.split("+")[0] in OK_EMAIL_LOCALS)


def scan_text(text, pats):
    """Devuelve [(línea, motivo)]; nunca incluye el dato privado."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            if not email_ok(m.group()):
                out.append((n, f"correo ({m.group()[:2]}…@{m.group().rpartition('@')[2]})"))
        for m in PATH.finditer(line):
            if m.group(1).lower() not in PLACEHOLDER and not m.group(1).startswith("."):
                out.append((n, "ruta personal (carpeta de usuario sin marcador)"))
        if any(not line[:m.start()].endswith((">/", ">\\")) for m in DRIVE.finditer(line)):
            out.append((n, "ruta personal (carpeta de Drive sin marcador)"))
        f = fold(line)
        for num, p in pats:
            if (p in f) if isinstance(p, str) else p.search(f):
                out.append((n, f"lista privada, patrón nº {num}"))
    return out


def scan_name(name, pats):
    return [(0, why) for _, why in scan_text(name, pats)]


def is_binary(b):
    return b"\0" in b[:8000]


def report(hits):
    for where, n, why in hits:
        print(f"  {where}:{n or '(nombre)'}  {why}", file=sys.stderr)
    if hits:
        print(f"\nBLOQUEADO: {len(hits)} coincidencia(s) con datos personales. Arréglalo o, si es un marcador "
              "legítimo, añádelo a las listas permitidas del script (sin saltarte la barrera).", file=sys.stderr)
        sys.exit(1)
    print("check_privado: ok")


def mode_staged(pats):
    hits = []
    for name in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split("\0"):
        if not name:
            continue
        hits += [(name, n, w) for n, w in scan_name(name, pats)]
        blob = subprocess.run(["git", "show", f":{name}"], capture_output=True).stdout
        if not is_binary(blob):
            hits += [(name, n, w) for n, w in scan_text(blob.decode("utf-8", errors="replace"), pats)]
    report(hits)


def mode_push(pats):
    commits = []
    for line in sys.stdin.read().splitlines():
        parts = line.split()
        if len(parts) == 4 and set(parts[1]) != {"0"}:
            commits += git("rev-list", parts[1], "--not", "--remotes").split()
    hits = []
    for c in dict.fromkeys(commits):
        short = c[:8]
        meta = git("log", "-1", "--format=%an%n%ae%n%ce%n%B", c)
        hits += [(f"commit {short} (autor/mensaje)", n, w) for n, w in scan_text(meta, pats)]
        path = None
        lineno = 0
        for l in git("show", "--format=", "-m", "--first-parent", "-U0", "--no-color", "--no-ext-diff", c).splitlines():
            if l.startswith("+++ "):
                path = l[6:] if l.startswith("+++ b/") else None
            elif l.startswith("@@"):
                m = re.search(r"\+(\d+)", l)
                lineno = int(m.group(1)) - 1 if m else 0
            elif l.startswith("+") and path:
                lineno += 1
                hits += [(f"{path} @{short}", lineno, w) for _, w in scan_text(l[1:], pats)]
    report(hits)


def mode_all(pats, root):
    root = Path(root).resolve()
    hits = []
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts or not f.is_file() or f.name == "desktop.ini":
            continue
        hits += [(rel.as_posix(), n, w) for n, w in scan_name(rel.as_posix(), pats)]
        b = f.read_bytes()
        if not is_binary(b):
            hits += [(rel.as_posix(), n, w) for n, w in scan_text(b.decode("utf-8", errors="replace"), pats)]
    report(hits)


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    override = None
    if "--patrones" in argv:
        i = argv.index("--patrones")
        override = argv[i + 1]
        del argv[i:i + 2]
    if not argv or argv[0] not in ("--staged", "--push", "--all"):
        sys.exit(__doc__)
    pats = load_patterns(override)
    if argv[0] == "--staged":
        mode_staged(pats)
    elif argv[0] == "--push":
        mode_push(pats)
    else:
        mode_all(pats, argv[1] if len(argv) > 1 else git("rev-parse", "--show-toplevel").strip() or ".")


if __name__ == "__main__":
    main(sys.argv[1:])
