"""Genera index.html y Mapeo_Establecimientos_Oruro.docx a partir de establecimientos_oruro.csv.

Uso: python3 generar.py
"""
import csv
import json
import os

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = os.path.dirname(os.path.abspath(__file__))
FECHA = "19/10/2026"
SECTORES = ["Estatal", "Seguridad social", "Privado"]
PRIORIDADES = {"Alta": "Prioridad alta", "Licitación": "Licitación / compra pública", "Media": "Por verificar"}
NOTA = ("Datos obtenidos de búsquedas web (prensa local, Sedes, Ministerio de Salud, directorios y redes sociales). "
        "No se pudo consultar Google Maps directamente: confirmar dirección y teléfono antes de visitar.")
PROVINCIAS = ("No se encontraron clínicas privadas en las provincias; los pacientes se derivan a la ciudad de Oruro. "
              "Puede haber consultorios pequeños sin presencia en internet: pedir al Sedes el registro de "
              "establecimientos privados habilitados por municipio.")
PASOS = [
    "Sedes Oruro: pedir el registro de establecimientos habilitados (públicos y privados) por municipio, y los habilitados en 2025-2026.",
    "Ministerio de Salud: listado de establecimientos del SUS en Oruro (Estab_Oruro.pdf).",
    "Google Maps: buscar “clínica / centro médico / consultorio / laboratorio / odontología” en cada municipio; priorizar locales con pocas reseñas y recientes.",
    "Facebook: buscar “inauguración clínica Oruro”, “consultorio Huanuni”, “dentista Challapata”; revisar fecha de creación de cada página.",
    "SICOES: suscribirse a convocatorias de Gobernación, Sedes, GAMO, alcaldías de provincia, UPRE, CNS y Caja Petrolera con rubro “equipamiento médico”.",
]


def leer():
    with open(os.path.join(BASE, "establecimientos_oruro.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generar_html(rows):
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    pasos = "".join(f"<li>{p}</li>" for p in PASOS)
    html = HTML.replace("__DATA__", data).replace("__FECHA__", FECHA).replace("__NOTA__", NOTA)
    html = html.replace("__PROVINCIAS__", PROVINCIAS).replace("__PASOS__", pasos)
    html = html.replace("__PRIO__", json.dumps(PRIORIDADES, ensure_ascii=False))
    with open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def sombrear(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def generar_docx(rows):
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(1.8))
    estilo = doc.styles["Normal"]
    estilo.font.name = "Arial"
    estilo.font.size = Pt(9)

    t = doc.add_paragraph()
    t.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = t.add_run("MAPEO DE ESTABLECIMIENTOS DE SALUD – DEPARTAMENTO DE ORURO")
    r.bold = True
    r.font.size = Pt(15)
    p = doc.add_paragraph(f"Estatales, seguridad social y privados · Prospección para venta de equipo médico · {FECHA}")
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    n = doc.add_paragraph()
    n.add_run("Nota: ").bold = True
    n.add_run(NOTA)

    doc.add_heading("Resumen", level=2)
    for s in SECTORES:
        sub = [x for x in rows if x["sector"] == s]
        prov = sum(1 for x in sub if x["municipio"] != "Oruro")
        doc.add_paragraph(f"{s}: {len(sub)} registros ({len(sub) - prov} en la ciudad de Oruro, {prov} en provincias).",
                          style="List Bullet")
    ops = [x for x in rows if x["prioridad"] in ("Alta", "Licitación")]
    doc.add_paragraph(f"Oportunidades activas (prioridad alta o compra pública): {len(ops)}.", style="List Bullet")

    cols = [("nombre", "Nombre", 4.6), ("tipo", "Tipo", 3), ("nivel", "Nivel", 2.6), ("municipio", "Municipio", 2.2),
            ("direccion", "Dirección", 4.2), ("telefono", "Teléfono", 2), ("novedad", "Novedad / oportunidad", 6.4)]
    for i, s in enumerate(SECTORES, 1):
        doc.add_heading(f"{i}. {s}", level=2)
        tbl = doc.add_table(rows=1, cols=len(cols))
        tbl.style = "Table Grid"
        for j, (_, h, _) in enumerate(cols):
            c = tbl.rows[0].cells[j]
            c.text = ""
            rr = c.paragraphs[0].add_run(h)
            rr.bold = True
            rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            sombrear(c, "0B6E6E")
        for x in sorted((x for x in rows if x["sector"] == s), key=lambda x: (x["municipio"] != "Oruro", x["municipio"])):
            cells = tbl.add_row().cells
            for j, (k, _, _) in enumerate(cols):
                cells[j].text = x[k]
            if x["prioridad"] in ("Alta", "Licitación"):
                for c in cells:
                    sombrear(c, "E3F2F1")
        for row in tbl.rows:
            for j, (_, _, w) in enumerate(cols):
                row.cells[j].width = Cm(w)
        if s == "Privado":
            doc.add_paragraph().add_run("Provincias: ").bold = True
            doc.paragraphs[-1].add_run(PROVINCIAS)
    doc.add_paragraph("Filas sombreadas: prioridad alta o compra pública en curso.").runs[0].italic = True

    doc.add_heading(f"{len(SECTORES) + 1}. Cómo completar el mapeo", level=2)
    for s in PASOS:
        doc.add_paragraph(s, style="List Bullet")

    doc.add_heading(f"{len(SECTORES) + 2}. Fuentes", level=2)
    for u in sorted({x["enlace"] for x in rows if x["enlace"]}):
        doc.add_paragraph(u, style="List Bullet")

    doc.save(os.path.join(BASE, "Mapeo_Establecimientos_Oruro.docx"))


HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Establecimientos de Salud Oruro</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#66665f;--line:#e2e2dc;--accent:#0b6e6e;--est:#0b6e6e;--seg:#8a5a00;--pri:#5a5a8a;--hl:#e3f2f1}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--fg:#ececea;--muted:#a3a39b;--line:#33332f;--accent:#4fc1c1;--est:#4fc1c1;--seg:#e0ac4a;--pri:#a7a7e0;--hl:#1d3332}}
:root[data-theme="dark"]{--bg:#151514;--card:#1f1f1d;--fg:#ececea;--muted:#a3a39b;--line:#33332f;--accent:#4fc1c1;--est:#4fc1c1;--seg:#e0ac4a;--pri:#a7a7e0;--hl:#1d3332}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.7rem;margin:0 0 4px}
h2{font-size:1.15rem;margin:32px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--muted);margin:0 0 16px}
.note{background:var(--card);border-left:4px solid var(--seg);padding:10px 14px;border-radius:6px;font-size:.92rem;margin:8px 0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.stat b{display:block;font-size:1.6rem;line-height:1.2}
.stat span{color:var(--muted);font-size:.85rem}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;align-items:center}
.filters button,select,input[type=search]{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 12px;border-radius:999px;font:inherit;font-size:.9rem}
.filters button{cursor:pointer}
.filters button.on{background:var(--accent);border-color:var(--accent);color:var(--bg)}
input[type=search]{flex:1;min-width:180px}
label.chk{font-size:.9rem;display:flex;gap:6px;align-items:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card.op{background:var(--hl)}
.card h3{margin:0 0 6px;font-size:1rem}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.tag{font-size:.72rem;font-weight:600;padding:2px 8px;border-radius:999px;border:1px solid currentColor}
.s-Estatal{color:var(--est)}.s-Seguridad{color:var(--seg)}.s-Privado{color:var(--pri)}
.tag.p{color:var(--fg)}
.card p{margin:4px 0;font-size:.9rem;overflow-wrap:anywhere}
.k{color:var(--muted)}
a{color:var(--accent);overflow-wrap:anywhere}
ul{padding-left:20px}
li{margin:4px 0}
.empty{color:var(--muted)}
</style>
</head>
<body>
<main>
<h1>Establecimientos de salud – Oruro</h1>
<p class="sub">Estatales, seguridad social y privados · ciudad y provincias · relevamiento al __FECHA__</p>
<p class="note">__NOTA__</p>
<div class="stats" id="stats"></div>

<h2>Listado</h2>
<div class="filters" id="sector">
  <button class="on" data-v="all">Todos</button>
  <button data-v="Estatal">Estatales</button>
  <button data-v="Seguridad social">Seguridad social</button>
  <button data-v="Privado">Privados</button>
</div>
<div class="filters">
  <select id="ambito" aria-label="Ámbito">
    <option value="all">Ciudad y provincias</option>
    <option value="ciudad">Solo ciudad de Oruro</option>
    <option value="prov">Solo provincias</option>
  </select>
  <label class="chk"><input type="checkbox" id="op"> Solo oportunidades</label>
  <input type="search" id="q" placeholder="Buscar nombre, tipo, municipio…" aria-label="Buscar">
</div>
<div class="grid" id="grid"></div>
<p class="empty" id="empty" hidden>Sin resultados.</p>

<h2>Clínicas privadas en provincias</h2>
<p>__PROVINCIAS__</p>

<h2>Cómo completar el mapeo</h2>
<ul>__PASOS__</ul>
</main>
<script>
const D=__DATA__;
const P=__PRIO__;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const isOp=x=>x.prioridad==="Alta"||x.prioridad==="Licitación";
let sector="all";
function stats(){
  const n=f=>D.filter(f).length;
  const S=[["Estatales",n(x=>x.sector==="Estatal")],["Seguridad social",n(x=>x.sector==="Seguridad social")],
    ["Privados",n(x=>x.sector==="Privado")],["En provincias",n(x=>x.municipio!=="Oruro")],["Oportunidades activas",n(isOp)]];
  document.getElementById("stats").innerHTML=S.map(([t,v])=>`<div class="stat"><b>${v}</b><span>${t}</span></div>`).join("");
}
function render(){
  const q=document.getElementById("q").value.toLowerCase();
  const amb=document.getElementById("ambito").value;
  const op=document.getElementById("op").checked;
  const rows=D.filter(x=>(sector==="all"||x.sector===sector)
    &&(amb==="all"||(amb==="ciudad")===(x.municipio==="Oruro"))
    &&(!op||isOp(x))
    &&[x.nombre,x.tipo,x.municipio,x.novedad].join(" ").toLowerCase().includes(q))
    .sort((a,b)=>isOp(b)-isOp(a));
  document.getElementById("grid").innerHTML=rows.map(x=>{
    const maps="https://www.google.com/maps/search/"+encodeURIComponent(x.nombre+" "+(x.municipio==="Provincias"?"":x.municipio)+" Oruro Bolivia");
    const links=(x.enlace?`<a href="${esc(x.enlace)}" target="_blank" rel="noopener">Fuente</a> · `:"")+`<a href="${maps}" target="_blank" rel="noopener">Google Maps</a>`;
    const f=(k,v)=>v?`<p><span class="k">${k}:</span> ${esc(v)}</p>`:"";
    return `<div class="card${isOp(x)?" op":""}"><div class="tags"><span class="tag s-${x.sector.split(" ")[0]}">${esc(x.sector)}</span>${x.prioridad?`<span class="tag p">${P[x.prioridad]}</span>`:""}</div>
<h3>${esc(x.nombre)}</h3>${f("Tipo",x.tipo)}${f("Nivel",x.nivel)}${f("Municipio",x.municipio)}${f("Dirección",x.direccion)}${f("Teléfono",x.telefono)}${f("Novedad",x.novedad)}<p>${links}</p></div>`}).join("");
  document.getElementById("empty").hidden=rows.length>0;
}
document.getElementById("sector").addEventListener("click",e=>{
  const v=e.target.dataset.v;if(!v)return;sector=v;
  document.querySelectorAll("#sector button").forEach(b=>b.classList.toggle("on",b===e.target));render();});
["ambito","op","q"].forEach(id=>document.getElementById(id).addEventListener("input",render));
stats();render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    filas = leer()
    generar_html(filas)
    generar_docx(filas)
    print(f"{len(filas)} registros -> index.html, Mapeo_Establecimientos_Oruro.docx")
