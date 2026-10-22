"""Texts of the windows and messages of costlog.py / carpetas.py / send.py / statusline.py in the person's language (IDIOMA in
kit-datos.yaml). textos.json next to this file = {"Spanish text": "translation"}: the install copies textos.en.json
(IDIOMA: en) or translates it into IDIOMA; no textos.json (IDIOMA: es), or a missing key -> Spanish.
Keep in each translation the {placeholders}, the commands (costlog>, `_<carpeta>:`, exit >…) and the emoji.
  python textos.py --test [file.json]   every T("…") in the scripts has a translation with the same {placeholders}
                                        (default textos.en.json; pass textos.json to check a new language).
                                        Texts of scripts not installed (e.g. send.py deleted) are only counted."""
import ast, json, os, string, sys

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    TX = json.load(open(os.path.join(HERE, "textos.json"), encoding="utf-8"))
except (OSError, ValueError):
    TX = {}


def T(s, **k):
    t = TX.get(s) or s
    try:
        return t.format(**k) if k else t
    except (KeyError, IndexError, ValueError):  # a broken translation never breaks the script: Spanish instead
        return s.format(**k)


def keys():
    """Every T("literal") in the scripts next to this file -> {text: file}."""
    out = {}
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".py") and f != "textos.py":
            for n in ast.walk(ast.parse(open(os.path.join(HERE, f), encoding="utf-8").read())):
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "T" and isinstance(n.args[0], ast.Constant):
                    out[n.args[0].value] = f
    return out


def fields(s):
    return sorted(f for _, f, _, _ in string.Formatter().parse(s) if f)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] != ["--test"]:
        sys.exit(__doc__)
    path = os.path.join(HERE, sys.argv[2] if len(sys.argv) > 2 else "textos.en.json")
    tr, ks = json.load(open(path, encoding="utf-8")), keys()
    bad = [f"missing ({f}): {k}" for k, f in ks.items() if k not in tr]
    bad += [f"placeholders differ: {k} -> {v}" for k, v in tr.items() if k in ks and fields(k) != fields(v)]
    unused = sum(k not in ks for k in tr)  # harmless: a script that isn't installed (send.py is optional)
    TX.clear()
    TX.update({"Hola {n}": "Hi {n}", "Roto": "Broken {x}"})
    assert T("Hola {n}", n=2) == "Hi 2" and T("Roto") == "Broken {x}" and T("Otro") == "Otro"
    TX["Roto {a}"] = "Broken {b}"
    assert T("Roto {a}", a=1) == "Roto 1"  # bad translation -> Spanish, no crash
    if bad:
        sys.exit("\n".join(bad))
    print(f"ok textos ({len(ks)} texts, {os.path.basename(path)})" + (f"; {unused} not used here" if unused else ""))
