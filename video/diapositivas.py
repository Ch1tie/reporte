"""Renderiza las imágenes generadas (estilo del video original) a PNG 1920x1080."""
import html
import json
import os
import re
import subprocess
import sys

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1280px;height:720px;overflow:hidden;font-family:Inter,sans-serif;color:#1d1d1f;
 background:#f7f6f2;background-image:linear-gradient(#e9e7e1 1px,transparent 1px),linear-gradient(90deg,#e9e7e1 1px,transparent 1px);
 background-size:32px 32px;position:relative}
mark{background:linear-gradient(transparent 12%,#ffe25a 12%,#ffe25a 92%,transparent 92%);color:inherit;padding:0 .08em}
.emo{font-family:'Noto Color Emoji';line-height:1}
.card{background:#fff;border:3px solid #1d1d1f;border-radius:26px;box-shadow:12px 12px 0 #f39cf0}
.foot{position:absolute;right:28px;bottom:18px;font-size:15px;color:#9a9a9a;letter-spacing:.04em}
.blob{position:absolute;border-radius:50%;background:#f9c9f5;opacity:.55;z-index:-1}
.wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px 80px;z-index:1}
h1{font-weight:700;letter-spacing:-.02em;text-align:center;line-height:1.12}
.sub{font-size:30px;color:#555;margin-top:18px;text-align:center}
.lab{font-size:17px;font-weight:700;letter-spacing:.14em;color:#c43dbb;margin-bottom:10px}
.mid{width:96px;height:96px;border-radius:50%;background:#f39cf0;border:3px solid #1d1d1f;display:flex;align-items:center;justify-content:center;font-size:48px;font-weight:800;flex:none}
"""


def md(t):
    t = html.escape(t)
    return re.sub(r"\*\*(.+?)\*\*", r"<mark>\1</mark>", t)


def emo(e, size):
    return f'<div class="emo" style="font-size:{size}px">{html.escape(e)}</div>'


def blobs():
    return ('<div class="blob" style="width:420px;height:420px;left:-120px;top:-140px"></div>'
            '<div class="blob" style="width:300px;height:300px;right:-80px;bottom:-110px"></div>')


ILUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ilustraciones")


def big(s):
    sub = f'<div class="sub">{md(s["s"])}</div>' if s.get("s") else ""
    ilus = os.path.join(ILUS, s.get("_id", "") + ".png")
    if s.get("_id") and os.path.exists(ilus):
        fs = 54 if len(s["h"]) < 34 else 46
        return f'''<img src="file://{ilus}" style="position:absolute;left:50%;top:40px;transform:translateX(-50%);height:470px;max-width:1120px;object-fit:contain;border-radius:22px">
      <div style="position:absolute;left:0;right:0;bottom:44px;display:flex;flex-direction:column;align-items:center">
      <h1 class="card" style="font-size:{fs}px;padding:14px 36px;max-width:1120px">{md(s["h"])}</h1></div>'''
    n = len(s["h"])
    fs = 76 if n < 28 else 64 if n < 42 else 54
    return f'''{blobs()}<div class="wrap">{emo(s["e"], 170)}
      <h1 style="font-size:{fs}px;margin-top:36px;max-width:1080px">{md(s["h"])}</h1>{sub}</div>'''


def duo(s):
    def side(x, lab):
        e, t, sub = x
        l = f'<div class="lab">{lab}</div>' if lab else ""
        return f'''<div class="card" style="width:430px;height:390px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px">
          {l}{emo(e, 130)}<div style="font-size:{40 if len(t) < 18 else 32}px;font-weight:700;margin-top:22px;text-align:center">{md(t)}</div>
          <div style="font-size:24px;color:#666;margin-top:8px;text-align:center">{md(sub)}</div></div>'''
    head = f'<h1 style="font-size:50px;margin-bottom:34px">{md(s["head"])}</h1>' if s.get("head") else ""
    return f'''{blobs()}<div class="wrap">{head}<div style="display:flex;align-items:center;gap:44px">
      {side(s["a"], s.get("la"))}<div class="mid">{html.escape(s.get("mid", "="))}</div>{side(s["b"], s.get("lb"))}</div></div>'''


def lista(s):
    items = s["items"]
    if s.get("grid"):
        cells = "".join(
            f'<div class="card" style="width:250px;height:250px;display:flex;flex-direction:column;align-items:center;justify-content:center">'
            f'{emo(e, 100)}<div style="font-size:28px;font-weight:700;margin-top:18px;text-align:center;padding:0 10px">{md(t)}</div></div>'
            for e, t in items)
        body = f'<div style="display:flex;gap:34px">{cells}</div>'
    else:
        rows = "".join(
            f'<div class="card" style="width:820px;display:flex;align-items:center;gap:30px;padding:18px 34px;margin:14px 0">'
            f'{emo(e, 72)}<div style="font-size:40px;font-weight:600">{md(t)}</div></div>' for e, t in items)
        body = f'<div>{rows}</div>'
    return f'{blobs()}<div class="wrap"><h1 style="font-size:54px;margin-bottom:34px">{md(s["head"])}</h1>{body}</div>'


def flow(s):
    arrow = s.get("arrow", "➜")
    parts = []
    for i, (e, t) in enumerate(s["steps"]):
        if i:
            parts.append(f'<div style="font-size:60px;font-weight:800;color:#c43dbb">{html.escape(arrow)}</div>')
        w = 230 if len(s["steps"]) > 3 else 300
        parts.append(f'<div class="card" style="width:{w}px;height:260px;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                     f'{emo(e, 110)}<div style="font-size:30px;font-weight:700;margin-top:20px;text-align:center">{md(t)}</div></div>')
    return f'''{blobs()}<div class="wrap"><h1 style="font-size:56px;margin-bottom:46px">{md(s["head"])}</h1>
      <div style="display:flex;align-items:center;gap:26px">{"".join(parts)}</div></div>'''


def stat(s):
    return f'''{blobs()}<div class="wrap"><div class="card" style="padding:40px 110px;text-align:center">
      <div style="font-size:250px;font-weight:900;letter-spacing:-.04em;line-height:1;color:#fff;-webkit-text-stroke:6px #1d1d1f;text-shadow:12px 12px 0 #f39cf0">{html.escape(s["n"])}</div>
      <div style="font-size:46px;font-weight:600;margin-top:20px">{md(s["h"])}</div></div></div>'''


def section(s):
    return f'''<div style="position:absolute;inset:0;background:#f39cf0"></div>
      <div style="position:absolute;left:40px;top:70px;font-size:520px;font-weight:900;line-height:1;color:#fff;-webkit-text-stroke:8px #1d1d1f">{s["n"]}</div>
      <div class="card" style="position:absolute;left:330px;top:170px;width:1050px;height:380px;padding:60px 70px;box-shadow:none;border-radius:190px 0 0 190px;border-right:none">
        <div style="font-size:70px;font-weight:500;letter-spacing:-.02em">{md(s["h"])}</div>
        <div style="font-size:32px;color:#444;margin-top:14px">{md(s["s"])}</div>
        <div class="emo" style="font-size:90px;margin-top:40px;letter-spacing:30px">{html.escape(s["e"])}</div></div>'''


def quote(s):
    return f'''{blobs()}<div class="wrap"><div class="card" style="padding:90px 80px 60px;max-width:1040px;position:relative">
      <div style="position:absolute;top:-30px;left:40px;font-size:200px;font-weight:900;color:#f39cf0;line-height:1">“</div>
      <div style="font-size:56px;font-weight:600;line-height:1.25">{md(s["h"])}</div>
      <div style="font-size:26px;color:#777;margin-top:30px">— Lo que señalan los expertos</div></div></div>'''


RENDER = {"big": big, "duo": duo, "list": lista, "flow": flow, "stat": stat, "section": section, "quote": quote}


def pagina(spec):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body>{RENDER[spec["t"]](spec)}<div class="foot">StarCraft y Empresa</div></body></html>')


def renderizar(specs, salida):
    """specs: lista de (nombre, spec). Escribe HTML y los captura con Playwright (Node)."""
    os.makedirs(salida, exist_ok=True)
    trabajos = []
    for nombre, spec in specs:
        h = os.path.join(salida, nombre + ".html")
        open(h, "w", encoding="utf-8").write(pagina(spec))
        trabajos.append([h, os.path.join(salida, nombre + ".png")])
    lista = os.path.join(salida, "trabajos.json")
    json.dump(trabajos, open(lista, "w"))
    subprocess.run(["node", os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturar.js"), lista], check=True)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from tomas import TOMAS
    specs = [(f"g{i:03d}", s) for i, (_, s) in enumerate(TOMAS) if s["t"] != "orig"]
    renderizar(specs, sys.argv[1])
    print(len(specs), "imágenes")
