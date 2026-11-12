#!/usr/bin/env python3
"""
Comprueba los años de canciones.json contra MusicBrainz (fecha de primera publicación).

Solo informa; no cambia ningún año. Con --confirmar quita la marca "revisar" de las
canciones cuyo año coincide con MusicBrainz.

Uso:
  python tools/verificar_anios.py                   # todas
  python tools/verificar_anios.py --solo-revisar    # solo las marcadas con revisar
  python tools/verificar_anios.py --solo-revisar --confirmar

MusicBrainz pide como máximo 1 petición por segundo, así que tarda unos minutos.
El resultado es una ayuda: ante una discrepancia, mira el disco/single original en
MusicBrainz o Discogs y decide tú.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Nuhitster/1.0 (proyecto personal de juego musical)"


def norm(t):
    t = t.lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = t.replace("&", "and")
    t = re.sub(r"[^a-z0-9áéíóúüñæ ]+", " ", t)
    t = re.sub(r"^the ", "", t.strip())
    return re.sub(r"\s+", " ", t).strip()


def consulta(titulo, artista):
    q = f'recording:"{titulo}" AND artist:"{artista}"'
    url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode({"query": q, "fmt": "json", "limit": 25})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("recordings", [])


def anio_mb(s):
    t_norm, a_norm = norm(s["titulo"]), norm(s["artista"])
    anios = []
    for rec in consulta(s["titulo"], s["artista"]):
        fecha = rec.get("first-release-date") or ""
        if not re.match(r"^\d{4}", fecha):
            continue
        titulo_rec = norm(rec.get("title", ""))
        credito = norm(" ".join(c.get("name", "") for c in rec.get("artist-credit", []) if isinstance(c, dict)))
        if (titulo_rec == t_norm or t_norm in titulo_rec or titulo_rec in t_norm) and (a_norm in credito or credito in a_norm):
            anios.append(int(fecha[:4]))
    return min(anios) if anios else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(Path(__file__).resolve().parent.parent / "canciones.json"))
    ap.add_argument("--solo-revisar", action="store_true")
    ap.add_argument("--confirmar", action="store_true", help="Quita 'revisar' donde coincide el año")
    a = ap.parse_args()

    ruta = Path(a.json)
    canciones = json.load(open(ruta, encoding="utf-8"))
    objetivo = [s for s in canciones if s.get("revisar")] if a.solo_revisar else canciones

    difieren, sin_datos, ok = [], [], 0
    for n, s in enumerate(objetivo, 1):
        try:
            mb = anio_mb(s)
        except Exception as ex:
            print(f"[{n}/{len(objetivo)}] {s['id']} error de red: {ex}")
            mb = None
        if mb is None:
            sin_datos.append(s)
            estado = "sin datos"
        elif mb == s["anio"]:
            ok += 1
            estado = "OK"
            if a.confirmar:
                s.pop("revisar", None)
        else:
            difieren.append((s, mb))
            estado = f"DIFIERE (MusicBrainz: {mb})"
        print(f"[{n}/{len(objetivo)}] {s['id']} {s['artista']} - {s['titulo']}: json {s['anio']} -> {estado}")
        time.sleep(1.1)

    if a.confirmar:
        json.dump(canciones, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    print(f"\nCoinciden: {ok} · Difieren: {len(difieren)} · Sin datos: {len(sin_datos)}")
    for s, mb in difieren:
        print(f"  {s['id']} {s['artista']} - {s['titulo']}: json {s['anio']} vs MusicBrainz {mb}")
    if sin_datos:
        print("Sin datos (comprobar a mano):", ", ".join(s["id"] for s in sin_datos))


if __name__ == "__main__":
    main()
