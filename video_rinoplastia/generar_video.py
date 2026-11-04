#!/usr/bin/env python3
"""Genera un video educativo sobre rinoplastia.

- Imagenes de cada escena: Gemini (modelo de imagen) si existe GEMINI_API_KEY;
  si no, ilustraciones de respaldo generadas localmente.
- El doctor aparece en la escena de presentacion y en el cierre (assets/doctor.jpg).

Uso:
    export GEMINI_API_KEY=...            # opcional
    python3 generar_video.py --doctor "Dr. Nombre Apellido" --clinica "Clinica X"
Salida: salida/video_rinoplastia.mp4
"""
import argparse
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30
FADE = 0.7
BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
OUT = BASE / "salida"
GEN = OUT / "imagenes"
TMP = OUT / "tmp"

FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
if not Path(FONT_REG).exists():
    FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

ESTILO = ("Ilustracion medica educativa, estilo limpio y profesional, colores suaves "
          "azul y turquesa, iluminacion clinica, sin texto ni letras en la imagen, 16:9.")

ESCENAS = [
    {"id": "01_titulo", "tipo": "titulo", "dur": 6,
     "titulo": "Rinoplastia", "sub": "Todo lo que necesitas saber",
     "prompt": "Perfil lateral elegante de un rostro humano con lineas suaves que resaltan la nariz, fondo degradado azul. " + ESTILO},
    {"id": "02_doctor", "tipo": "doctor", "dur": 8,
     "titulo": "Te acompaña tu especialista",
     "puntos": ["Valoración personalizada", "Resultados naturales y armónicos", "Seguridad en cada etapa"]},
    {"id": "03_que_es", "dur": 8, "titulo": "¿Qué es la rinoplastia?",
     "puntos": ["Cirugía que modifica la forma y el tamaño de la nariz",
                "Puede ser estética, funcional o ambas",
                "Busca armonía con el resto del rostro"],
     "prompt": "Diagrama anatomico de la nariz humana en vista lateral mostrando hueso nasal y cartilagos. " + ESTILO},
    {"id": "04_motivos", "dur": 8, "titulo": "¿Por qué se realiza?",
     "puntos": ["Giba o joroba nasal", "Punta caída o ancha",
                "Desviación del tabique y dificultad para respirar",
                "Secuelas de traumatismos"],
     "prompt": "Comparacion de varias siluetas de nariz en perfil (recta, con giba, punta caida), ilustracion medica. " + ESTILO},
    {"id": "05_tecnicas", "dur": 8, "titulo": "Técnicas: abierta y cerrada",
     "puntos": ["Abierta: pequeña incisión en la columela, mayor visibilidad",
                "Cerrada: incisiones dentro de la nariz, sin cicatriz externa",
                "El cirujano elige según cada caso"],
     "prompt": "Ilustracion medica comparando rinoplastia abierta y cerrada en una nariz, vista inferior y lateral. " + ESTILO},
    {"id": "06_procedimiento", "dur": 8, "titulo": "El día de la cirugía",
     "puntos": ["Anestesia general o sedación", "Duración aproximada: 1.5 a 3 horas",
                "Se colocan férula y, si es necesario, taponamiento"],
     "prompt": "Quirofano moderno y luminoso, equipo quirurgico preparado, ambiente seguro y limpio, sin pacientes visibles. " + ESTILO},
    {"id": "07_recuperacion", "dur": 8, "titulo": "Recuperación",
     "puntos": ["Semana 1: férula, inflamación y moretones leves",
                "Semanas 2-3: retorno a actividades normales",
                "6-12 meses: resultado definitivo"],
     "prompt": "Linea de tiempo visual de recuperacion con calendario y una persona descansando tranquila en casa con ferula nasal. " + ESTILO},
    {"id": "08_cuidados", "dur": 8, "titulo": "Cuidados después de la cirugía",
     "puntos": ["Dormir con la cabeza elevada", "Evitar sol, golpes y lentes pesados",
                "No sonarse con fuerza", "Asistir a todos los controles"],
     "prompt": "Iconos ilustrados de cuidados postoperatorios: almohada elevada, sol tachado, compresa fria, calendario de controles. " + ESTILO},
    {"id": "09_riesgos", "dur": 7, "titulo": "Riesgos a conocer",
     "puntos": ["Sangrado, infección o asimetrías", "Posible necesidad de retoque",
                "Elegir un cirujano certificado reduce los riesgos"],
     "prompt": "Escudo medico con cruz y checklist de seguridad, ilustracion profesional. " + ESTILO},
    {"id": "10_cierre", "tipo": "cierre", "dur": 7,
     "titulo": "Agenda tu valoración",
     "sub": "Resuelve tus dudas con tu especialista"},
]


# ---------------------------------------------------------------- Gemini
def gemini_imagen(prompt: str, destino: Path, key: str, modelo: str) -> bool:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": "16:9"}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.load(r)
        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                destino.write_bytes(base64.b64decode(inline["data"]))
                return True
        print("  Gemini no devolvio imagen:", json.dumps(data)[:300])
    except Exception as e:  # noqa: BLE001
        print("  Error Gemini:", e)
    return False


# ---------------------------------------------------------------- helpers
def gradiente(c1, c2, size=(W, H)):
    img = Image.new("RGB", size, c1)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        t = y / size[1]
        d.line([(0, y), (size[0], y)],
               fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def respaldo(idx: int) -> Image.Image:
    """Ilustracion abstracta de respaldo (cuando no hay Gemini)."""
    paletas = [((10, 40, 80), (20, 120, 150)), ((15, 60, 90), (40, 150, 160)),
               ((20, 35, 70), (60, 110, 170))]
    c1, c2 = paletas[idx % len(paletas)]
    img = gradiente(c1, c2)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for k in range(6):
        r = 180 + 60 * ((idx + k) % 4)
        x = (idx * 311 + k * 397) % W
        y = (idx * 173 + k * 251) % H
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 18))
    # silueta estilizada de perfil
    pts = [(1250, 220), (1300, 380), (1330, 470), (1420, 640), (1400, 680),
           (1330, 690), (1340, 760), (1320, 900)]
    d.line(pts, fill=(255, 255, 255, 90), width=10, joint="curve")
    capa = capa.filter(ImageFilter.GaussianBlur(2))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def cubrir(img: Image.Image, size=(W, H)) -> Image.Image:
    img = img.convert("RGB")
    s = max(size[0] / img.width, size[1] / img.height)
    img = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    l, t = (img.width - size[0]) // 2, (img.height - size[1]) // 2
    return img.crop((l, t, l + size[0], t + size[1]))


def envolver(texto, font, ancho, draw):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if draw.textlength(prueba, font=font) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas


def foto_doctor_circular(diam: int) -> Image.Image:
    foto = Image.open(ASSETS / "doctor.jpg").convert("RGB")
    # recorte centrado en el rostro (foto 960x1280)
    cx, cy, lado = int(foto.width * 0.42), int(foto.height * 0.44), int(foto.width * 0.66)
    foto = foto.crop((cx - lado // 2, cy - lado // 2, cx + lado // 2, cy + lado // 2))
    foto = foto.resize((diam, diam), Image.LANCZOS)
    mask = Image.new("L", (diam * 4, diam * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diam * 4, diam * 4], fill=255)
    mask = mask.resize((diam, diam), Image.LANCZOS)
    out = Image.new("RGBA", (diam + 24, diam + 24), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, diam + 23, diam + 23], fill=(94, 234, 212, 255))
    out.paste(foto, (12, 12), mask)
    return out


# ---------------------------------------------------------------- capas
def capa_texto(esc, args) -> Image.Image:
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f_tit = ImageFont.truetype(FONT_BOLD, 78)
    f_txt = ImageFont.truetype(FONT_REG, 44)
    f_peq = ImageFont.truetype(FONT_REG, 30)
    acento = (94, 234, 212, 255)
    tipo = esc.get("tipo", "info")

    # sombra lateral para legibilidad
    sombra = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sombra)
    for x in range(W):
        a = max(0, int(200 * (1 - x / (W * 0.72))))
        sd.line([(x, 0), (x, H)], fill=a)
    capa.paste((5, 15, 30, 255), (0, 0), sombra)
    d = ImageDraw.Draw(capa)

    if tipo in ("titulo", "cierre"):
        f_big = ImageFont.truetype(FONT_BOLD, 130 if tipo == "titulo" else 96)
        y = 360 if tipo == "titulo" else 300
        d.rectangle([140, y - 40, 260, y - 30], fill=acento)
        d.text((140, y), esc["titulo"], font=f_big, fill="white")
        y += 170 if tipo == "titulo" else 130
        d.text((140, y), esc["sub"], font=f_txt, fill=(220, 235, 245))
        if tipo == "cierre":
            foto = foto_doctor_circular(420)
            capa.alpha_composite(foto, (W - foto.width - 180, (H - foto.height) // 2 - 40))
            nx = W - foto.width - 180 + foto.width // 2
            ny = (H + foto.height) // 2 - 10
            for txt, f in ((args.doctor, ImageFont.truetype(FONT_BOLD, 44)),
                           (args.clinica, f_peq)):
                if txt:
                    d.text((nx - d.textlength(txt, font=f) / 2, ny), txt, font=f, fill="white")
                    ny += 56
            if args.contacto:
                d.text((140, y + 90), args.contacto, font=f_txt, fill=acento)
        return capa

    if tipo == "doctor":
        foto = foto_doctor_circular(560)
        capa.alpha_composite(foto, (W - foto.width - 200, (H - foto.height) // 2 - 30))
        nombre_x = W - foto.width - 200 + foto.width // 2
        f_n = ImageFont.truetype(FONT_BOLD, 48)
        ny = (H + foto.height) // 2 - 10
        for txt, f in ((args.doctor, f_n), (args.especialidad, f_peq)):
            if txt:
                d.text((nombre_x - d.textlength(txt, font=f) / 2, ny), txt, font=f, fill="white")
                ny += 62

    x, y = 140, 230
    d.rectangle([x, y - 40, x + 120, y - 30], fill=acento)
    for linea in envolver(esc["titulo"], f_tit, 1000, d):
        d.text((x, y), linea, font=f_tit, fill="white")
        y += 96
    y += 40
    for p in esc.get("puntos", []):
        d.ellipse([x, y + 18, x + 18, y + 36], fill=acento)
        for linea in envolver(p, f_txt, 860, d):
            d.text((x + 44, y), linea, font=f_txt, fill=(235, 242, 248))
            y += 58
        y += 26
    d.text((140, H - 80), "Contenido informativo. Consulta siempre a un cirujano certificado.",
           font=f_peq, fill=(190, 205, 215))
    return capa


def fondo(esc, idx, key, modelo) -> Image.Image:
    if esc.get("tipo") == "doctor" or esc.get("tipo") == "cierre":
        # fondo desenfocado a partir de la foto del doctor
        f = cubrir(Image.open(ASSETS / "doctor.jpg")).filter(ImageFilter.GaussianBlur(28))
        return Image.blend(f, gradiente((8, 30, 60), (15, 90, 120)), 0.55)
    destino = GEN / f"{esc['id']}.png"
    if not destino.exists() and key:
        print(f"  Gemini -> {esc['id']}")
        gemini_imagen(esc["prompt"], destino, key, modelo)
    if destino.exists():
        return cubrir(Image.open(destino))
    return respaldo(idx)


# ---------------------------------------------------------------- video
def render_clip(esc, idx, args, key) -> Path:
    bg = fondo(esc, idx, key, args.modelo)
    bg_path, tx_path = TMP / f"{esc['id']}_bg.png", TMP / f"{esc['id']}_tx.png"
    # margen extra para el efecto Ken Burns
    cubrir(bg, (int(W * 1.12), int(H * 1.12))).save(bg_path)
    capa_texto(esc, args).save(tx_path)
    clip = TMP / f"{esc['id']}.mp4"
    frames = int(esc["dur"] * FPS)
    zoom = f"zoompan=z='1+0.08*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
    filtro = (f"[0:v]{zoom},format=yuv420p[bg];"
              f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.8:alpha=1[tx];"
              f"[bg][tx]overlay=0:0,format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(bg_path),
                    "-loop", "1", "-i", str(tx_path), "-filter_complex", filtro,
                    "-t", str(esc["dur"]), "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                    "-crf", "20", str(clip)], check=True)
    return clip


def unir(clips, durs, musica, salida):
    entradas, filtros = [], []
    for c in clips:
        entradas += ["-i", str(c)]
    prev, offset = "[0:v]", 0.0
    for i in range(1, len(clips)):
        offset += durs[i - 1] - FADE
        etiqueta = f"[v{i}]"
        filtros.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}{etiqueta}")
        prev = etiqueta
    total = sum(durs) - FADE * (len(clips) - 1)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *entradas]
    mapa = ["-map", prev]
    if musica:
        cmd += ["-i", str(musica)]
        filtros.append(f"[{len(clips)}:a]volume=0.35,afade=t=out:st={total - 2:.2f}:d=2[a]")
        mapa += ["-map", "[a]", "-shortest", "-c:a", "aac"]
    cmd += ["-filter_complex", ";".join(filtros), *mapa, "-c:v", "libx264", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(salida)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doctor", default="", help="Nombre del doctor")
    ap.add_argument("--especialidad", default="Cirugía Plástica y Estética Facial")
    ap.add_argument("--clinica", default="")
    ap.add_argument("--contacto", default="", help="Teléfono, web o redes")
    ap.add_argument("--musica", default="", help="Ruta a un mp3 opcional")
    ap.add_argument("--modelo", default="gemini-2.5-flash-image")
    args = ap.parse_args()

    for p in (GEN, TMP):
        p.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("GEMINI_API_KEY", "")
    print("Imágenes:", "Gemini" if key else "respaldo local (sin GEMINI_API_KEY)")

    clips = []
    for i, esc in enumerate(ESCENAS):
        print(f"Escena {esc['id']}")
        clips.append(render_clip(esc, i, args, key))
    salida = OUT / "video_rinoplastia.mp4"
    unir(clips, [e["dur"] for e in ESCENAS], args.musica, salida)
    print("Listo:", salida)


if __name__ == "__main__":
    main()
