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
import time

import nuh_common as nc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(nc.JSON_POR_DEFECTO))
    ap.add_argument("--solo-revisar", action="store_true")
    ap.add_argument("--confirmar", action="store_true", help="Quita 'revisar' donde coincide el año")
    a = ap.parse_args(argv)

    canciones = nc.leer_json(a.json)
    objetivo = [s for s in canciones if s.get("revisar")] if a.solo_revisar else canciones

    difieren, sin_datos, ok = [], [], 0
    try:
        for n, s in enumerate(objetivo, 1):
            try:
                mb = nc.anio_musicbrainz(s["titulo"], s["artista"])
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
                    s.pop("nota", None)
            else:
                difieren.append((s, mb))
                estado = f"DIFIERE (MusicBrainz: {mb})"
            print(f"[{n}/{len(objetivo)}] {s['id']} {s['artista']} - {s['titulo']}: json {s['anio']} -> {estado}")
            time.sleep(1.1)
    except KeyboardInterrupt:
        print("\nInterrumpido.")

    if a.confirmar:
        nc.guardar_json(a.json, canciones)

    print(f"\nCoinciden: {ok} · Difieren: {len(difieren)} · Sin datos: {len(sin_datos)}")
    for s, mb in difieren:
        print(f"  {s['id']} {s['artista']} - {s['titulo']}: json {s['anio']} vs MusicBrainz {mb}")
    if sin_datos:
        print("Sin datos (comprobar a mano):", ", ".join(s["id"] for s in sin_datos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
