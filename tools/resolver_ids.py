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
import time

import nuh_common as nc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(nc.JSON_POR_DEFECTO))
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--ids", help="Lista de ids separada por comas")
    ap.add_argument("--limite", type=int)
    a = ap.parse_args(argv)

    canciones = nc.leer_json(a.json)
    objetivo = canciones
    if a.ids:
        ids = set(a.ids.split(","))
        objetivo = [s for s in canciones if s["id"] in ids]
    if not a.forzar:
        objetivo = [s for s in objetivo if not s.get("yt")]
    if a.limite:
        objetivo = objetivo[:a.limite]
    if not objetivo:
        print("Nada que resolver: todas las canciones elegidas ya tienen yt.")
        return 0

    flat, full = nc.crear_ydl()
    fallos = []
    try:
        for n, s in enumerate(objetivo, 1):
            try:
                info = nc.buscar_youtube(flat, full, s)
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
                nc.guardar_json(a.json, canciones)
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nInterrumpido: guardo lo hecho hasta ahora.")
    nc.guardar_json(a.json, canciones)
    print(f"\nHecho. {len(objetivo) - len(fallos)} resueltas, {len(fallos)} sin resultado.")
    if fallos:
        print("Sin resultado (ponles yt a mano):", ", ".join(s["id"] for s in fallos))
    print("Revisa los pares artista/título contra el canal y título de YouTube impresos arriba.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
