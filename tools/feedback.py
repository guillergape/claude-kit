#!/usr/bin/env python3
"""Manda el informe al autor del kit por su formulario de Google: sin correo, sin cuentas, solo stdlib.

    feedback.py <LAB>/INFORME_MIGRACION.md --nombre "<Nombre>" --tipo instalacion|uso|actualizacion
        enseña lo que se mandaría (campos y tamaño) y NO manda nada
    ... --enviar     lo manda (solo con el OK de la persona)
    feedback.py --nombre "<Nombre>" --tipo actualizacion [--enviar]
        sin informe: solo nombre, versión y tipo (para que el autor sepa cuántos lo usan/actualizan)
    feedback.py --test

Lo recibe solo el autor (una fila por informe en su hoja de cálculo: fecha, nombre, versión, tipo, fallos,
ideas, informe entero). Antes de mandar, la carpeta de usuario se cambia por <HOME>.
Salida: 0 = enviado (o vista previa) · 2 = no se pudo (sin formulario, sin internet...) → plan B: correo.
"""
import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Enlace "rellenado previamente" del formulario del autor, con cada respuesta = el nombre de su campo
# (nombre, version, tipo, fallos, ideas, informe). Vacío = sin formulario → plan B.
ENLACE = "https://docs.google.com/forms/d/e/1FAIpQLSdYfMHrroWNsgEsO3Y8kmYza91lvBziuqdHJYRzVgCm_m0TuQ/viewform?usp=pp_url&entry.918851962=nombre&entry.1871535119=version&entry.1931361514=tipo&entry.644411058=fallos&entry.113221989=ideas&entry.665910754=informe"
CAMPOS = ("nombre", "version", "tipo", "fallos", "ideas", "informe")
MAX = 49000  # una celda de Google Sheets admite 50 000 caracteres


def destino(enlace):
    url, _, query = enlace.partition("?")
    ids = {v: k for k, v in urllib.parse.parse_qsl(query) if k.startswith("entry.")}
    falta = [c for c in CAMPOS if c not in ids]
    if falta:
        raise ValueError(f"al enlace le faltan los campos: {', '.join(falta)}")
    return url.replace("/viewform", "/formResponse"), ids


def seccion(texto, *claves):
    """Cuerpo de la primera sección `## ` cuyo título contiene alguna clave (es/en), sin comentarios <!-- -->."""
    for bloque in re.split(r"^## ", texto, flags=re.M)[1:]:
        titulo, _, cuerpo = bloque.partition("\n")
        if any(c in titulo.lower() for c in claves):
            return re.sub(r"<!--.*?-->", "", cuerpo, flags=re.S).strip()
    return ""


def campos(informe, nombre, tipo, home=None):
    home = str(home or Path.home())
    for h in {home, home.replace("\\", "/")}:
        informe = informe.replace(h, "<HOME>")
    version = (Path(__file__).resolve().parent.parent / "VERSION.txt")
    version = version.read_text(encoding="utf-8").splitlines()[0].split(":", 1)[-1].strip() if version.exists() else "?"
    if len(informe) > MAX:  # ponytail: se recorta; si pasa, el resto va por correo
        informe = informe[:MAX] + "\n[…recortado: el resto por correo]"
    return {"nombre": nombre, "version": version, "tipo": tipo,
            "fallos": seccion(informe, "fall", "fail", "bug")[:MAX],
            "ideas": seccion(informe, "idea")[:MAX], "informe": informe}


def enviar(datos, enlace):
    url, ids = destino(enlace)
    cuerpo = urllib.parse.urlencode({ids[k]: v for k, v in datos.items()}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo), timeout=30) as r:
        return r.status


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # consola de Windows: emojis del informe
    p = argparse.ArgumentParser()
    p.add_argument("informe", nargs="?")
    p.add_argument("--nombre")
    p.add_argument("--tipo", default="instalacion")
    p.add_argument("--enviar", action="store_true")
    p.add_argument("--test", action="store_true")
    a = p.parse_args(argv)
    if a.test:
        return test()
    if not a.nombre:
        p.error("hace falta --nombre")
    datos = campos(Path(a.informe).read_text(encoding="utf-8") if a.informe else "", a.nombre, a.tipo)
    for k, v in datos.items():
        linea = v.strip().splitlines()[0][:80] if v.strip() else "(vacío)"
        print(f"{k:8} {len(v):6} caracteres · {linea}")
    if not a.enviar:
        print("Vista previa: no se ha mandado nada. Con el OK de la persona, repite con --enviar.")
        return 0
    if not ENLACE:
        print("PLAN B: este kit no tiene formulario configurado (ENLACE vacío). Manda el informe por correo.")
        return 2
    try:
        print(f"Enviado al autor del kit (HTTP {enviar(datos, ENLACE)}).")
        return 0
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"PLAN B: no se pudo enviar ({e}). Manda el informe por correo.")
        return 2


def test():
    import http.server
    import threading
    recibido = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            recibido.append((self.path, self.rfile.read(int(self.headers["Content-Length"])).decode()))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    enlace = (f"http://127.0.0.1:{srv.server_port}/forms/d/e/X/viewform?usp=pp_url&"
              + "&".join(f"entry.{i}={c}" for i, c in enumerate(CAMPOS)))
    home = "C:\\" + "Usuarios\\ana"
    informe = ("# Informe — Ana\n## Sistema\n- Lab: " + home + "\\claude-lab y " + home.replace("\\", "/") + "\n"
               "## What failed or had bugs\n<!-- comentario -->\nmd2pdf: ñ€ error\n## Chats aparte\nnada\n"
               "## Ideas / peticiones para el autor del kit\nmás tests\n## Uso\n")
    datos = campos(informe, "Ana", "instalacion", home=home)
    assert "<HOME>\\claude-lab y <HOME>" in datos["informe"] and home not in datos["informe"]
    assert datos["fallos"] == "md2pdf: ñ€ error" and datos["ideas"] == "más tests", datos
    assert enviar(datos, enlace) == 200
    path, cuerpo = recibido[0]
    q = dict(urllib.parse.parse_qsl(cuerpo))
    assert path == "/forms/d/e/X/formResponse" and q["entry.0"] == "Ana" and q["entry.4"] == "más tests", q
    assert q["entry.5"] == datos["informe"]
    try:
        destino(enlace.replace("&entry.5=informe", ""))
        raise AssertionError("faltaba informe y no falló")
    except ValueError:
        pass
    assert len(campos("x" * (MAX + 10), "A", "uso", home=home)["informe"]) < MAX + 50
    solo = campos("", "Ana", "actualizacion", home=home)  # aviso sin informe: solo nombre, versión y tipo
    assert solo["informe"] == solo["fallos"] == solo["ideas"] == "" and solo["tipo"] == "actualizacion"
    assert main(["--nombre", "Ana", "--tipo", "actualizacion"]) == 0  # vista previa, no manda
    srv.shutdown()
    print("feedback.py --test: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
