"""Rellena una plantilla del kit con los datos de la persona (kit-datos.yaml).

    python rellenar.py <plantilla> [--datos <LAB>/kit-datos.yaml] [-o <salida>]
    python rellenar.py --test

Cada clave de primer nivel de kit-datos.yaml con valor simple (`LAB: /home/ana/claude-lab`) sustituye
a <CLAVE> en la plantilla (`<LAB>`). Lo indentado, las listas y las claves vacías no se tocan: los lee
Claude. Sin -o escribe en stdout. Al final avisa (stderr) de los <…> que quedan por rellenar a mano;
no cuenta HTML ni las marcas <!-- kit:… -->.
Esa lista incluye también los que son parte de la sintaxis de un comando (<fichero>, <audio>…): esos se quedan.
Solo stdlib: el .yaml se lee línea a línea (subconjunto simple de YAML), sin PyYAML.
"""
import re, sys
from pathlib import Path

KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*?)[ \t]*$")
LEFT = re.compile(r"<(?!!--|/|(?:div|br|span|strong|em|b|i|p|a|sub|sup|details|summary)\b)[^<>\n]+>")


def leer_datos(path):
    datos = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = KEY.match(line)
        if not m:
            continue
        v = m.group(2)
        q = re.match(r""""((?:[^"\\]|\\.)*)"|'((?:[^']|'')*)'""", v)  # como en YAML: "…\"…" y '…''…'
        if q:
            v = re.sub(r'\\(["\\])', r"\1", q.group(1)) if q.group(1) is not None else q.group(2).replace("''", "'")
        else:
            v = re.split(r"(?:^|\s)#", v)[0].rstrip()  # sin el comentario del final (o solo comentario: vacío)
        if v and v not in ("[]", "{}", "|", ">"):
            datos[m.group(1)] = v
    return datos


def rellenar(texto, datos):
    for k, v in datos.items():
        texto = texto.replace(f"<{k}>", v)
    return texto, sorted(set(LEFT.findall(texto)))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if argv[0] == "--test":
        return test()
    plantilla, datos_path, out = Path(argv[0]), None, None
    if "--datos" in argv:
        datos_path = argv[argv.index("--datos") + 1]
    if "-o" in argv:
        out = argv[argv.index("-o") + 1]
    if not datos_path:
        sys.exit("Falta --datos <LAB>/kit-datos.yaml")
    texto, quedan = rellenar(plantilla.read_text(encoding="utf-8"), leer_datos(datos_path))
    if out:
        Path(out).write_text(texto, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(texto)
    if quedan:
        sys.stderr.reconfigure(encoding="utf-8")
        print(f"\nQuedan por rellenar a mano ({len(quedan)}): " + " · ".join(quedan), file=sys.stderr)


def test():
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "kit-datos.yaml")
        Path(d).write_text('# comentario\nNombre: Ana\nLAB: "/home/ana/claude lab"\nPY: python3   # Mac/Linux\n'
                           'CORREO: ""\nX: "" # comentario\nY: \'a # b\'  # c\nasignaturas:   # comentario\n  - corto: Prog\nmodulos: []\n'
                           'P1: "x \\"<f>\\" (\'y\')"  # c\nP2: \'it\'\'s "z"\'\n', encoding="utf-8")
        datos = leer_datos(d)
        assert datos == {"Nombre": "Ana", "LAB": "/home/ana/claude lab", "PY": "python3", "Y": "a # b",
                         "P1": 'x "<f>" (\'y\')', "P2": 'it\'s "z"'}, datos
        t, quedan = rellenar('<!-- kit:x -->\n<div>Hola <Nombre></div>\n`<PY> "<LAB>/a.py"` <CORREO> <cuenta por defecto><br>', datos)
        assert '<div>Hola Ana</div>' in t and '`python3 "/home/ana/claude lab/a.py"`' in t, t
        assert quedan == ["<CORREO>", "<cuenta por defecto>"], quedan
    print("ok rellenar")


if __name__ == "__main__":
    main(sys.argv[1:])
