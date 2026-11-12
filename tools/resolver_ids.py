#!/usr/bin/env python3
"""
Busca en YouTube un vídeo para cada canción de canciones.json y rellena el campo "yt".

Solo acepta vídeos que YouTube permite incrustar (playable_in_embed), de duración razonable
y sin pinta de directo/cover/remix. Guarda también "yt_titulo" y "yt_canal" para que
puedas revisar rápido si es el vídeo correcto.

Uso (en tu ordenador, no hace falta login):
  pip install yt-dlp
  python tools/resolver_ids.py                 # solo las canciones sin yt
  python tools/resolver_ids.py --forzar        # rehace todas
  python tools/resolver_ids.py --ids 001,002   # solo esas
  python tools/resolver_ids.py --limite 20     # prueba con 20

Se hace copia de seguridad en canciones.json.bak antes de escribir.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Falta yt-dlp. Ejecuta:  pip install yt-dlp")

MALOS = ("live", "en vivo", "cover", "karaoke", "reaction", "tutorial", "lesson", "remix",
         "8d", "slowed", "sped up", "nightcore", "tribute", "parody", "how to play",
         "drum cam", "guitar cover", "bass cover", "piano cover")


def puntuar(e, s):
    titulo = (e.get("title") or "").lower()
    canal = (e.get("channel") or e.get("uploader") or "").lower()
    puntos = 0
    artista = s["artista"].lower().replace("the ", "")
    if artista in canal or artista in titulo:
        puntos += 3
    if "topic" in canal or "vevo" in canal:
        puntos += 2
    if "official" in titulo:
        puntos += 1
    return puntos


def candidato_valido(e, s):
    titulo = (e.get("title") or "").lower()
    original = s["titulo"].lower()
    for mal in MALOS:
        if mal in titulo and mal not in original:
            return False
    dur = e.get("duration")
    if dur is not None and not (60 <= dur <= 1200):
        return False
    return True


def buscar(flat, full, s):
    q = f"{s['artista']} {s['titulo']} official audio"
    res = flat.extract_info(f"ytsearch8:{q}", download=False)
    entradas = [e for e in (res.get("entries") or []) if e and candidato_valido(e, s)]
    entradas.sort(key=lambda e: -puntuar(e, s))  # sort estable: mantiene el orden de YouTube
    for e in entradas[:5]:
        try:
            info = full.extract_info(f"https://www.youtube.com/watch?v={e['id']}", download=False)
        except Exception:
            continue
        if info.get("playable_in_embed") is False or info.get("availability") not in (None, "public", "unlisted"):
            continue
        return info
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(Path(__file__).resolve().parent.parent / "canciones.json"))
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--ids", help="Lista de ids separada por comas")
    ap.add_argument("--limite", type=int)
    a = ap.parse_args()

    ruta = Path(a.json)
    canciones = json.load(open(ruta, encoding="utf-8"))
    shutil.copy(ruta, str(ruta) + ".bak")

    objetivo = canciones
    if a.ids:
        ids = set(a.ids.split(","))
        objetivo = [s for s in canciones if s["id"] in ids]
    if not a.forzar:
        objetivo = [s for s in objetivo if not s.get("yt")]
    if a.limite:
        objetivo = objetivo[:a.limite]

    base = {"quiet": True, "no_warnings": True, "skip_download": True}
    flat = yt_dlp.YoutubeDL({**base, "extract_flat": True})
    full = yt_dlp.YoutubeDL(base)

    fallos = []
    for n, s in enumerate(objetivo, 1):
        try:
            info = buscar(flat, full, s)
        except Exception as ex:
            info = None
            print(f"  ! error en {s['id']}: {ex}")
        if info:
            s["yt"] = info["id"]
            s["yt_titulo"] = info.get("title", "")
            s["yt_canal"] = info.get("channel") or info.get("uploader") or ""
            print(f"[{n}/{len(objetivo)}] {s['id']} {s['artista']} - {s['titulo']}  ->  {s['yt']}  ({s['yt_canal']}: {s['yt_titulo']})")
        else:
            fallos.append(s)
            print(f"[{n}/{len(objetivo)}] {s['id']} {s['artista']} - {s['titulo']}  ->  SIN RESULTADO")
        if n % 10 == 0:
            json.dump(canciones, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        time.sleep(0.4)

    json.dump(canciones, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"\nHecho. {len(objetivo) - len(fallos)} resueltas, {len(fallos)} sin resultado.")
    if fallos:
        print("Sin resultado (ponles yt a mano):", ", ".join(s["id"] for s in fallos))
    print("Revisa los pares artista/título contra el canal y título de YouTube impresos arriba.")


if __name__ == "__main__":
    main()
