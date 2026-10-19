"""Genera index.html y Mapeo_Establecimientos_Oruro.docx a partir de establecimientos_oruro.csv.

Ambos muestran una sola tabla con todos los establecimientos (nuevos y antiguos).
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
NOTA = ("Datos obtenidos de búsquedas web (prensa local, Sedes, Ministerio de Salud, directorios, aseguradoras y redes "
        "sociales). Varios teléfonos y datos de terapia intensiva vienen de fuentes de 2020-2021: confirmar antes de visitar.")
PROVINCIAS = ("En las provincias no se encontraron clínicas privadas; solo hospitales y centros de salud públicos.")
CRITERIO = ("Antigüedad: «Nueva» = abierta desde 2021; «Antigua» = más de 5 años; «En obra» / «Proyecto» = todavía no "
            "funciona. Filas sombreadas: oportunidad activa (clínica nueva o en expansión, o compra pública en curso).")

# Columnas de la tabla: (campo, título, ancho en cm para el Word)
COLUMNAS = [
    ("n", "N°", 0.8), ("nombre", "Establecimiento", 4), ("sector", "Sector", 1.9), ("tipo", "Tipo / rubro", 2.3),
    ("nivel", "Nivel", 1.9), ("antiguedad", "Nueva / antigua", 1.7), ("apertura", "Apertura", 2),
    ("uti", "Terapia intensiva", 2), ("emergencia", "Emergencia", 1.6), ("municipio", "Municipio", 1.7),
    ("direccion", "Dirección", 3.2), ("telefono", "Teléfono", 2.2), ("novedad", "Novedad / oportunidad", 4.3),
]
ORDEN_SECTOR = {"Privado": 0, "Seguridad social": 1, "Estatal": 2}
ORDEN_NIVEL = ["3er", "2do", "1er-2do", "1er", "Policlínico", "Universitaria"]


def es_oportunidad(x):
    return x["prioridad"] in ("Alta", "Licitación")


def orden(x):
    nivel = next((i for i, n in enumerate(ORDEN_NIVEL) if x["nivel"].startswith(n)), len(ORDEN_NIVEL))
    return (ORDEN_SECTOR[x["sector"]], x["municipio"] != "Oruro", nivel, x["nombre"])


def leer():
    with open(os.path.join(BASE, "establecimientos_oruro.csv"), encoding="utf-8") as f:
        filas = sorted(csv.DictReader(f), key=orden)
    for i, x in enumerate(filas, 1):
        x["n"] = str(i)
    return filas


def generar_html(rows):
    cols = [{"k": k, "t": t} for k, t, _ in COLUMNAS]
    reemplazos = {
        "__DATA__": json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"),
        "__COLS__": json.dumps(cols, ensure_ascii=False),
        "__FECHA__": FECHA, "__NOTA__": NOTA, "__PROVINCIAS__": PROVINCIAS, "__CRITERIO__": CRITERIO,
    }
    html = HTML
    for k, v in reemplazos.items():
        html = html.replace(k, v)
    with open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def sombrear(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def repetir_encabezado(row):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader")
    h.set(qn("w:val"), "true")
    trPr.append(h)


def generar_docx(rows):
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(35.6), Cm(21.6)  # oficio horizontal: entra la tabla completa
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, m, Cm(1.2))
    estilo = doc.styles["Normal"]
    estilo.font.name = "Arial"
    estilo.font.size = Pt(7.5)

    t = doc.add_paragraph()
    t.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = t.add_run("CLÍNICAS Y ESTABLECIMIENTOS DE SALUD DE ORURO – NUEVOS Y ANTIGUOS")
    r.bold = True
    r.font.size = Pt(14)
    p = doc.add_paragraph(f"Privados, seguridad social y estatales · ciudad y provincias · relevamiento al {FECHA}")
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    cuenta = lambda f: sum(1 for x in rows if f(x))
    doc.add_paragraph(
        f"Total: {len(rows)} · privados: {cuenta(lambda x: x['sector'] == 'Privado')} · seguridad social: "
        f"{cuenta(lambda x: x['sector'] == 'Seguridad social')} · estatales: {cuenta(lambda x: x['sector'] == 'Estatal')} · "
        f"nuevos: {cuenta(lambda x: x['antiguedad'] == 'Nueva')} · antiguos: {cuenta(lambda x: x['antiguedad'] == 'Antigua')} · "
        f"en obra o proyecto: {cuenta(lambda x: x['antiguedad'] in ('En obra', 'Proyecto'))}.")
    for texto in (NOTA, CRITERIO, PROVINCIAS):
        doc.add_paragraph(texto).runs[0].italic = True

    tbl = doc.add_table(rows=1, cols=len(COLUMNAS))
    tbl.style = "Table Grid"
    repetir_encabezado(tbl.rows[0])
    for j, (_, titulo, _) in enumerate(COLUMNAS):
        c = tbl.rows[0].cells[j]
        c.text = ""
        rr = c.paragraphs[0].add_run(titulo)
        rr.bold = True
        rr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        sombrear(c, "0B6E6E")
    for x in rows:
        cells = tbl.add_row().cells
        for j, (k, _, _) in enumerate(COLUMNAS):
            cells[j].text = x[k]
        cells[1].paragraphs[0].runs[0].bold = True
        if es_oportunidad(x):
            for c in cells:
                sombrear(c, "E3F2F1")
    tbl.autofit = False
    for j, (_, _, w) in enumerate(COLUMNAS):
        tbl.columns[j].width = Cm(w)
        for c in tbl.columns[j].cells:
            c.width = Cm(w)

    doc.add_heading("Fuentes", level=2)
    for u in sorted({x["enlace"] for x in rows if x["enlace"]}):
        doc.add_paragraph(u, style="List Bullet")

    doc.save(os.path.join(BASE, "Mapeo_Establecimientos_Oruro.docx"))


HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clínicas de Oruro</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#66665f;--line:#e2e2dc;--accent:#0b6e6e;--warn:#8a5a00;--hl:#e3f2f1;--new:#0b6e6e;--old:#66665f;--obra:#8a5a00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--card:#1f1f1d;--fg:#ececea;--muted:#a3a39b;--line:#33332f;--accent:#4fc1c1;--warn:#e0ac4a;--hl:#1d3332;--new:#4fc1c1;--old:#a3a39b;--obra:#e0ac4a}}
:root[data-theme="dark"]{--bg:#151514;--card:#1f1f1d;--fg:#ececea;--muted:#a3a39b;--line:#33332f;--accent:#4fc1c1;--warn:#e0ac4a;--hl:#1d3332;--new:#4fc1c1;--old:#a3a39b;--obra:#e0ac4a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1600px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.6rem;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 12px}
.note{background:var(--card);border-left:4px solid var(--warn);padding:8px 14px;border-radius:6px;font-size:.88rem;margin:6px 0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:14px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stat b{display:block;font-size:1.5rem;line-height:1.2}
.stat span{color:var(--muted);font-size:.82rem}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;align-items:center}
select,input[type=search],button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 12px;border-radius:999px;font:inherit;font-size:.88rem}
button{cursor:pointer}
input[type=search]{flex:1;min-width:200px}
.count{color:var(--muted);font-size:.85rem;margin:4px 0}
.tw{overflow:auto;max-height:78vh;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:.84rem}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:var(--accent);color:var(--bg);font-weight:600;cursor:pointer;white-space:nowrap;user-select:none}
th:hover{text-decoration:underline}
tr.op td{background:var(--hl)}
td.nombre{font-weight:600;min-width:180px}
td.novedad{min-width:240px}
td.direccion{min-width:160px}
td.telefono{min-width:120px}
.b{display:inline-block;font-size:.75rem;font-weight:600;padding:1px 7px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.b-Nueva{color:var(--new)}.b-Antigua{color:var(--old)}.b-En{color:var(--obra)}.b-Proyecto{color:var(--obra)}.b-Por{color:var(--muted);border-style:dashed}
a{color:var(--accent)}
.empty{color:var(--muted);padding:12px}
</style>
</head>
<body>
<main>
<h1>Clínicas y establecimientos de salud de Oruro</h1>
<p class="sub">Nuevos y antiguos · privados, seguridad social y estatales · ciudad y provincias · relevamiento al __FECHA__</p>
<p class="note">__NOTA__</p>
<p class="note">__CRITERIO__ __PROVINCIAS__</p>
<div class="stats" id="stats"></div>
<div class="filters">
  <input type="search" id="q" placeholder="Buscar nombre, rubro, dirección…" aria-label="Buscar">
  <select id="f-sector" aria-label="Sector"><option value="">Todos los sectores</option><option>Privado</option><option>Seguridad social</option><option>Estatal</option></select>
  <select id="f-antiguedad" aria-label="Antigüedad"><option value="">Nuevas y antiguas</option><option>Nueva</option><option>Antigua</option><option value="obra">En obra / proyecto</option><option>Por confirmar</option></select>
  <select id="f-comp" aria-label="Complejidad"><option value="">Toda complejidad</option><option value="n3">3er nivel</option><option value="uti">Con terapia intensiva</option><option value="em">Con emergencia</option></select>
  <select id="f-amb" aria-label="Ámbito"><option value="">Ciudad y provincias</option><option value="ciudad">Solo ciudad de Oruro</option><option value="prov">Solo provincias</option></select>
  <button id="reset" type="button">Limpiar filtros</button>
</div>
<p class="count" id="count"></p>
<div class="tw"><table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table></div>
</main>
<script>
const D=__DATA__;
const COLS=__COLS__;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const C={n3:x=>x.nivel.includes("3er nivel"),uti:x=>x.uti.startsWith("Sí")||x.uti==="Neonatología",em:x=>x.emergencia.startsWith("Sí")};
const op=x=>x.prioridad==="Alta"||x.prioridad==="Licitación";
let sortK="n",sortDir=1;
const $=id=>document.getElementById(id);
function stats(){
  const n=f=>D.filter(f).length;
  const S=[["Total",D.length],["Privados",n(x=>x.sector==="Privado")],["Estatales y cajas",n(x=>x.sector!=="Privado")],
    ["Nuevos",n(x=>x.antiguedad==="Nueva")],["Antiguos",n(x=>x.antiguedad==="Antigua")],["En obra / proyecto",n(x=>x.antiguedad==="En obra"||x.antiguedad==="Proyecto")],
    ["3er nivel",n(C.n3)],["Con terapia intensiva",n(C.uti)],["Con emergencia",n(C.em)]];
  $("stats").innerHTML=S.map(([t,v])=>`<div class="stat"><b>${v}</b><span>${t}</span></div>`).join("");
}
function cell(x,k){
  const v=x[k]||"";
  if(k==="antiguedad")return `<span class="b b-${esc(v.split(" ")[0])}">${esc(v)}</span>`;
  if(k==="nombre"){
    const maps="https://www.google.com/maps/search/"+encodeURIComponent(x.nombre+" "+(x.municipio==="Provincias"?"":x.municipio)+" Oruro Bolivia");
    return esc(v)+`<br><a href="${maps}" target="_blank" rel="noopener">Maps</a>`+(x.enlace?` · <a href="${esc(x.enlace)}" target="_blank" rel="noopener">Fuente</a>`:"");
  }
  return esc(v)||"—";
}
function render(){
  const q=$("q").value.toLowerCase(),s=$("f-sector").value,a=$("f-antiguedad").value,c=$("f-comp").value,m=$("f-amb").value;
  const rows=D.filter(x=>(!s||x.sector===s)
    &&(!a||(a==="obra"?(x.antiguedad==="En obra"||x.antiguedad==="Proyecto"):x.antiguedad===a))
    &&(!c||C[c](x))&&(!m||(m==="ciudad")===(x.municipio==="Oruro"))
    &&[x.nombre,x.tipo,x.direccion,x.municipio,x.novedad].join(" ").toLowerCase().includes(q))
    .sort((p,r)=>{const A=p[sortK]||"",B=r[sortK]||"";return sortDir*(sortK==="n"?A-B:A.localeCompare(B,"es"));});
  $("head").innerHTML=COLS.map(o=>`<th data-k="${o.k}">${o.t}${o.k===sortK?(sortDir>0?" ▲":" ▼"):""}</th>`).join("");
  $("body").innerHTML=rows.length?rows.map(x=>`<tr class="${op(x)?"op":""}">${COLS.map(o=>`<td class="${o.k}">${cell(x,o.k)}</td>`).join("")}</tr>`).join("")
    :`<tr><td class="empty" colspan="${COLS.length}">Sin resultados.</td></tr>`;
  $("count").textContent=`Mostrando ${rows.length} de ${D.length}. Toque un encabezado para ordenar.`;
}
$("head").addEventListener("click",e=>{const k=e.target.dataset.k;if(!k)return;sortDir=k===sortK?-sortDir:1;sortK=k;render();});
["q","f-sector","f-antiguedad","f-comp","f-amb"].forEach(id=>$(id).addEventListener("input",render));
$("reset").addEventListener("click",()=>{$("q").value="";["f-sector","f-antiguedad","f-comp","f-amb"].forEach(id=>$(id).value="");render();});
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
