"""Genera la narración del guion con una voz de ElevenLabs.

Uso:
    ELEVENLABS_API_KEY=... python audio/generar_audio.py [--voz chitie] [--guion audio/guion_starcraft.txt]

Divide el guion por párrafos, genera cada uno pasando los IDs de las
peticiones anteriores (para mantener la entonación continua) y los une
en un solo MP3 con ffmpeg.
"""
import argparse
import os
import subprocess
import sys
import tempfile

import requests

API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"


def headers():
    # En la sesión en la nube el proxy inyecta la clave real; localmente usa la variable.
    return {"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")}


def buscar_voz(nombre):
    r = requests.get(f"{API}/voices", headers=headers(), timeout=60)
    r.raise_for_status()
    voces = r.json()["voices"]
    for v in voces:
        if v["name"].strip().lower() == nombre.lower():
            return v["voice_id"], v["name"]
    for v in voces:
        if nombre.lower() in v["name"].lower():
            return v["voice_id"], v["name"]
    disponibles = ", ".join(v["name"] for v in voces)
    sys.exit(f"No encontré la voz '{nombre}'. Voces disponibles: {disponibles}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--voz", default="chitie")
    p.add_argument("--guion", default=os.path.join(os.path.dirname(__file__), "guion_starcraft.txt"))
    p.add_argument("--salida", default=os.path.join(os.path.dirname(__file__), "starcraft_negocios.mp3"))
    a = p.parse_args()

    voice_id, nombre = buscar_voz(a.voz)
    print(f"Usando voz: {nombre} ({voice_id})")

    with open(a.guion, encoding="utf-8") as f:
        parrafos = [x.strip() for x in f.read().split("\n\n") if x.strip()]

    tmp = tempfile.mkdtemp()
    archivos, ids_previos = [], []
    for i, texto in enumerate(parrafos, 1):
        body = {
            "text": texto,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.2, "use_speaker_boost": True},
            "previous_request_ids": ids_previos[-3:],
        }
        r = requests.post(
            f"{API}/text-to-speech/{voice_id}?output_format=mp3_44100_128",
            headers={**headers(), "Content-Type": "application/json"},
            json=body,
            timeout=300,
        )
        if r.status_code != 200:
            sys.exit(f"Error en el párrafo {i}: {r.status_code} {r.text[:500]}")
        ruta = os.path.join(tmp, f"{i:02d}.mp3")
        with open(ruta, "wb") as out:
            out.write(r.content)
        archivos.append(ruta)
        if r.headers.get("request-id"):
            ids_previos.append(r.headers["request-id"])
        print(f"  párrafo {i}/{len(parrafos)} listo")

    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{x}'\n" for x in archivos)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lista, "-c", "copy", a.salida], check=True)
    print(f"Audio final: {a.salida}")


if __name__ == "__main__":
    main()
