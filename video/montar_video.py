"""Monta el video final: imágenes sincronizadas con la narración de ElevenLabs + música.

Uso:
    python video/montar_video.py --video ORIGINAL.mov --musica1 TERRAN.mp3 --musica2 TERRAN2.mp3 \
        --narracion audio/starcraft_negocios.mp3 --salida StarCraft_y_Empresa_voz_Chitie.mp4 --trabajo /tmp/trabajo
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from diapositivas import renderizar  # noqa: E402
from tiempos import calcular  # noqa: E402

FPS = 25
W, H = 1280, 720
MAX_TOMA = 6.3  # segundos; las tomas más largas se dividen con un acercamiento

# Momento (s) del video original donde cada diapositiva está completa.
ORIG_T = {"o01": 20, "o02": 50, "o03": 66, "o04": 75.5, "o05": 100, "o06": 113, "o07": 140,
          "o08": 170, "o09": 181.5, "o10": 205, "o11": 231, "o12": 236.5, "o13": 239.9}

# Recortes: (centro x, centro y, zoom) en fracciones de la imagen.
RECORTES = {
    "center": (0.5, 0.5, 1.35), "top": (0.5, 0.3, 1.4), "bottom": (0.5, 0.72, 1.4),
    "left": (0.25, 0.5, 2.0), "right": (0.75, 0.5, 2.0), "mid": (0.5, 0.5, 2.0),
}
ESPECIALES = {
    ("o01", "center"): (0.5, 0.62, 1.5), ("o02", "center"): (0.5, 0.45, 1.4),
    ("o07", "right"): (0.72, 0.5, 1.8), ("o11", "right"): (0.72, 0.5, 1.8),
    ("o08", "left"): (0.2, 0.42, 2.0), ("o08", "mid"): (0.5, 0.42, 2.0), ("o08", "right"): (0.78, 0.42, 1.7),
    ("o13", "top"): (0.5, 0.28, 1.9),
}
DETALLE = {"big": (0.5, 0.5, 1.25), "duo": (0.73, 0.55, 1.6)}


def sh(cmd):
    subprocess.run(cmd, check=True)


def recortar(src, dst, cx, cy, z):
    """Recorta una región 16:9 y la lleva a 1920x1080."""
    filtro = (f"scale=1920:1080:flags=lanczos,crop=iw/{z}:ih/{z}:"
              f"min(max(iw*{cx}-iw/{z}/2\\,0)\\,iw-iw/{z}):min(max(ih*{cy}-ih/{z}/2\\,0)\\,ih-ih/{z}),"
              f"scale=1920:1080:flags=lanczos")
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", filtro, "-frames:v", "1", dst])


def clip(img, n, idx, dst):
    """Clip de n fotogramas con un zoom lento (Ken Burns), alternando entrada/salida."""
    a, b = (1.0, 1.07) if idx % 2 == 0 else (1.07, 1.0)
    z = f"{a}+({b}-{a})*on/{max(n - 1, 1)}"
    vf = (f"scale=3840:2160:flags=lanczos,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={n}:s={W}x{H}:fps={FPS},format=yuv420p")
    sh(["ffmpeg", "-v", "error", "-y", "-i", img, "-vf", vf, "-frames:v", str(n),
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-r", str(FPS), dst])


def duracion(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).decode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--musica1", required=True)
    p.add_argument("--musica2", required=True)
    p.add_argument("--narracion", default=os.path.join(D, "..", "audio", "starcraft_negocios.mp3"))
    p.add_argument("--salida", required=True)
    p.add_argument("--trabajo", required=True)
    p.add_argument("--solo-audio", action="store_true", help="reutiliza el video mudo ya montado y solo rehace el audio")
    a = p.parse_args()
    T = a.trabajo
    for sub in ("orig", "gen", "img", "clips"):
        os.makedirs(os.path.join(T, sub), exist_ok=True)

    total = duracion(a.narracion) + 1.5
    tomas = calcular(total)

    mudo = os.path.join(T, "mudo.mp4")
    plan = []
    if not (a.solo_audio and os.path.exists(mudo)):
        # 1. Diapositivas originales
        for k, t in ORIG_T.items():
            sh(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", a.video, "-frames:v", "1",
                os.path.join(T, "orig", k + ".png")])

        # 2. Imágenes generadas
        from tomas import TOMAS
        gen = [(f"g{i:03d}", {**s, "_id": f"g{i:03d}"}) for i, (_, s) in enumerate(TOMAS) if s["t"] != "orig"]
        renderizar(gen, os.path.join(T, "gen"))

        # 3. Lista final de tomas (con división automática de las largas)
        plan = []
        for i, (s, e, spec, anc) in enumerate(tomas):
            if spec["t"] == "orig":
                base = os.path.join(T, "orig", spec["src"] + ".png")
                rec = spec.get("crop")
                reg = ESPECIALES.get((spec["src"], rec), RECORTES.get(rec)) if rec else (0.5, 0.5, 1.0)
            else:
                base = os.path.join(T, "gen", f"g{i:03d}.png")
                reg = (0.5, 0.5, 1.0)
            if e - s > MAX_TOMA:
                m = (s + e) / 2
                if spec["t"] == "orig":
                    det = (reg[0], reg[1], reg[2] * 1.15)
                else:
                    det = DETALLE.get(spec["t"], (0.5, 0.5, 1.18))
                plan += [(s, m, base, reg), (m, e, base, det)]
            else:
                plan.append((s, e, base, reg))

        # 4. Imágenes 1920x1080 por toma y clips
        def hacer(k):
            s, e, base, (cx, cy, z) = plan[k]
            img = os.path.join(T, "img", f"{k:03d}.png")
            recortar(base, img, cx, cy, z)
            n = round(e * FPS) - round(s * FPS)
            clip(img, n, k, os.path.join(T, "clips", f"{k:03d}.mp4"))
            return k

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
            for k in ex.map(hacer, range(len(plan))):
                print(f"  toma {k + 1}/{len(plan)}", flush=True)

        lista = os.path.join(T, "clips.txt")
        with open(lista, "w") as f:
            f.writelines(f"file '{os.path.join(T, 'clips', f'{k:03d}.mp4')}'\n" for k in range(len(plan)))
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", mudo])

    # 5. Audio: voz al frente (-13 LUFS, comprimida y con presencia) + música
    #    (Terran 1, luego Terran 2, y de nuevo Terran 1 si falta) que baja cuando hablas.
    fc = (
        "[1:a]aresample=44100,aformat=channel_layouts=stereo[m1];"
        "[2:a]aresample=44100,aformat=channel_layouts=stereo[m2];"
        "[3:a]aresample=44100,aformat=channel_layouts=stereo[m3];"
        "[m1][m2]acrossfade=d=3[m12];[m12][m3]acrossfade=d=3,"
        f"atrim=0:{total:.3f},loudnorm=I=-20:TP=-3,volume=0.6,"
        f"afade=t=in:d=1.5,afade=t=out:st={total - 4:.3f}:d=4[mus];"
        "[0:a]aresample=44100,aformat=channel_layouts=stereo,highpass=f=80,"
        "equalizer=f=3000:t=q:w=1.2:g=3,equalizer=f=200:t=q:w=1:g=-1.5,"
        "acompressor=threshold=0.1:ratio=3:attack=10:release=200:makeup=2,"
        "loudnorm=I=-13:TP=-1.2:LRA=7,apad=pad_dur=2,asplit=2[voz][sc];"
        "[mus][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=500[duck];"
        f"[voz][duck]amix=inputs=2:duration=first:normalize=0,atrim=0:{total:.3f},alimiter=limit=0.95[a]"
    )
    sh(["ffmpeg", "-v", "error", "-y", "-i", a.narracion, "-i", a.musica1, "-i", a.musica2, "-i", a.musica1,
        "-i", mudo, "-filter_complex", fc, "-map", "4:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.salida])
    print("Video final:", a.salida, f"({duracion(a.salida):.1f} s)")


if __name__ == "__main__":
    main()
