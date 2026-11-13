#!/usr/bin/env python3
"""
Importa canciones desde un CSV de Spotify a canciones.json, busca el vídeo de YouTube de
cada una, comprueba el año contra MusicBrainz y (opcionalmente) genera el PDF de cartas.

CÓMO SACAR EL CSV
  1. Entra en https://exportify.net e inicia sesión con tu cuenta de Spotify.
  2. Exporta una lista de reproducción (o "Liked Songs") a CSV.
  También vale cualquier CSV con columnas de título y artista (Track Name / Artist Name(s) /
  Release Date / Genres, o Title / Artist / Year...). Se detectan solas.

USO
  # Vista previa (sin red, sin escribir nada): qué entra, qué se descarta y cómo se clasifica
  python tools/importar_spotify.py mi_lista.csv --dry-run

  # Importar, buscar YouTube, corregir años y generar las cartas nuevas
  python tools/importar_spotify.py mi_lista.csv --cartas --base https://TUUSUARIO.github.io/Nuhitster/

  # Una lista que es toda de un mismo estilo
  python tools/importar_spotify.py thrash.csv --bloque metal --tema metal-moderno --forzar-tema

QUÉ HACE CON CADA CANCIÓN
  - Limpia el título ("- Remastered 2011", "(Mono)", "- 2015 Remaster"...).
  - Descarta las versiones en directo y las que ya están en canciones.json.
  - Clasifica en bloque y tema por los géneros de Spotify (si no hay género, usa --bloque/--tema).
  - Año: Spotify da el año del ÁLBUM (en remasterizaciones y recopilatorios sale mal). Se compara
    con MusicBrainz y se usa el más antiguo. Si difieren 2 años o más, o solo hay una fuente,
    queda marcada con "revisar" y una "nota" para que la mires.
  - Busca en YouTube un vídeo incrustable (campo yt) y se queda con canal y título para revisarlo.
Los ids nuevos empiezan en 300 (o tras el id más alto) y no se reutilizan nunca.
"""
import argparse
import collections
import csv
import io
import re
import sys
import time
from pathlib import Path

import nuh_common as nc

ALIAS = {
    "titulo": ["trackname", "name", "title", "track", "song", "songname", "titulo", "cancion"],
    "artista": ["artistnames", "artistname", "artists", "artist", "artista", "artistas"],
    "fecha": ["releasedate", "albumreleasedate", "releaseyear", "year", "anio", "ano", "fecha", "date"],
    "generos": ["genres", "genre", "artistgenres", "generos"],
    "album": ["albumname", "album"],
}

# Orden = prioridad: la primera regla que case con los géneros de Spotify decide el tema.
REGLAS = [
    (r"nu[ -]?metal|rap metal|funk metal", "nu-metal"),
    (r"gothic metal|gothic symphonic|dark metal", "gothic-metal"),
    (r"metalcore|deathcore|post-hardcore|screamo|electronicore", "metalcore"),
    (r"industrial", "industrial"),
    (r"alternative metal|alt metal|progressive metal|post-grunge|grunge|stoner|art metal", "alt-metal"),
    (r"gothic rock|goth rock|deathrock|death rock|gothic|batcave", "gothic-rock"),
    (r"darkwave|dark wave|coldwave|cold wave|dark electro|\bebm\b|minimal wave", "darkwave"),
    (r"synthpop|synth-pop|synth pop|new romantic|futurepop|electropop", "synthpop"),
    (r"post-punk|post punk|new wave|no wave", "post-punk"),
    (r"metal|hard rock|heavy", "metal-moderno"),
]
TEMA_POR_BLOQUE = {"metal": "metal-moderno", "gotico": "gothic-rock"}


# ---------------------------------------------------------------- Lectura del CSV
def clave_col(h):
    return re.sub(r"[^a-z0-9]", "", nc.quitar_acentos(str(h).lower()))


def leer_csv(ruta):
    """Devuelve (cabeceras, filas). Detecta codificación y separador."""
    raw = Path(ruta).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = raw.decode("utf-16")
    else:
        try:
            texto = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = raw.decode("cp1252", errors="replace")
    lineas = texto.splitlines()
    primera = lineas[0] if lineas else ""
    delim = max([",", ";", "\t"], key=primera.count)
    lector = csv.DictReader(io.StringIO(texto, newline=""), delimiter=delim)
    return lector.fieldnames or [], list(lector)


def mapear_columnas(cabeceras):
    por_clave = {clave_col(h): h for h in cabeceras if h}
    cols = {}
    for campo, alias in ALIAS.items():
        for al in alias:
            if al in por_clave:
                cols[campo] = por_clave[al]
                break
    return cols


def extraer(fila, cols):
    def g(campo):
        return (fila.get(cols[campo]) or "").strip() if campo in cols else ""
    titulo, artista = g("titulo"), g("artista")
    if not titulo or not artista:
        return None
    m = re.search(r"\b(19\d\d|20\d\d)\b", g("fecha"))
    return {
        "titulo": nc.limpiar_titulo(titulo) or titulo,
        "artista": artista.split(";")[0].strip(),   # Exportify separa artistas con ";"
        "anio_sp": int(m.group(1)) if m else None,
        "generos": g("generos"),
        "directo": nc.es_directo(titulo) or nc.es_directo(g("album")),
    }


# ---------------------------------------------------------------- Clasificación y año
def por_defecto(tema_def, bloque_def):
    if tema_def:
        return (bloque_def or nc.BLOQUE_DE_TEMA.get(tema_def) or "metal"), tema_def
    b = bloque_def or "metal"
    return b, TEMA_POR_BLOQUE[b]


def clasificar(generos, tema_def, bloque_def, forzar):
    """Devuelve (bloque, tema, por_genero)."""
    if not forzar:
        g = generos.lower()
        for patron, tema in REGLAS:
            if re.search(patron, g):
                return (nc.BLOQUE_DE_TEMA.get(tema) or bloque_def or "metal"), tema, True
    bloque, tema = por_defecto(tema_def, bloque_def)
    return bloque, tema, False


def resolver_anio(s, usar_mb):
    """Devuelve (año, revisar, nota) o None si no hay ningún año."""
    sp, mb = s["anio_sp"], None
    if usar_mb:
        try:
            mb = nc.anio_musicbrainz(s["titulo"], s["artista"])
        except Exception as ex:
            print(f"   ! MusicBrainz: {ex}")
        time.sleep(1.1)   # MusicBrainz admite 1 petición por segundo
    if sp and mb:
        nota = f"Spotify {sp}, MusicBrainz {mb}" if sp != mb else ""
        return min(sp, mb), abs(sp - mb) >= 2, nota
    if mb:
        return mb, True, "solo MusicBrainz"
    if sp:
        return sp, True, "año de Spotify sin verificar" if not usar_mb else "no encontrada en MusicBrainz; año de Spotify"
    return None


# ---------------------------------------------------------------- Principal
def main(argv=None):
    ap = argparse.ArgumentParser(description="Importa un CSV de Spotify a Nuhitster",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("csv", nargs="+", help="Uno o varios CSV")
    ap.add_argument("--json", default=str(nc.JSON_POR_DEFECTO), help="canciones.json de destino")
    ap.add_argument("--salida", help="Escribir en otro archivo en vez de actualizar --json")
    ap.add_argument("--bloque", choices=["metal", "gotico"], help="Bloque si Spotify no da género")
    ap.add_argument("--tema", choices=sorted(nc.TEMAS), help="Tema si Spotify no da género")
    ap.add_argument("--forzar-tema", action="store_true", help="Usar --bloque/--tema en todas, ignorando los géneros")
    ap.add_argument("--id-inicio", type=int, default=300, help="Primer id si no hay ninguno mayor (por defecto 300)")
    ap.add_argument("--incluir-live", action="store_true", help="No descartar versiones en directo")
    ap.add_argument("--sin-yt", action="store_true", help="No buscar vídeos de YouTube")
    ap.add_argument("--sin-mb", action="store_true", help="No comprobar años en MusicBrainz")
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar qué pasaría (sin red ni escritura)")
    ap.add_argument("--cartas", action="store_true", help="Generar el PDF con las cartas importadas")
    ap.add_argument("--base", help="URL pública de tu web (necesaria con --cartas)")
    ap.add_argument("--pdf", default="cartas_nuevas.pdf", help="Nombre del PDF (por defecto cartas_nuevas.pdf)")
    ap.add_argument("--tam", type=float, default=60, help="Lado de la carta en mm")
    a = ap.parse_args(argv)
    if a.cartas and not a.base:
        ap.error("--cartas necesita --base (la URL de tu web)")

    destino = Path(a.salida or a.json)
    existentes = nc.leer_json(a.json) if Path(a.json).exists() else []
    vistas = {nc.clave(s["artista"], s["titulo"]) for s in existentes}
    siguiente = max([int(s["id"]) for s in existentes if str(s["id"]).isdigit()] + [a.id_inicio - 1]) + 1

    # ---- 1. Leer, limpiar, filtrar, clasificar
    candidatas, stats, descartes = [], collections.Counter(), collections.defaultdict(list)
    for ruta in a.csv:
        cabeceras, filas = leer_csv(ruta)
        cols = mapear_columnas(cabeceras)
        if "titulo" not in cols or "artista" not in cols:
            sys.exit(f"{ruta}: no encuentro las columnas de título y artista. Cabeceras: {cabeceras}")
        print(f"{ruta}: {len(filas)} filas · columnas usadas: " + ", ".join(f"{k}='{v}'" for k, v in cols.items()))
        for fila in filas:
            s = extraer(fila, cols)
            if s is None:
                stats["filas vacías"] += 1
                continue
            etiqueta = f"{s['artista']} - {s['titulo']}"
            if s["directo"] and not a.incluir_live:
                stats["en directo"] += 1; descartes["en directo"].append(etiqueta); continue
            k = nc.clave(s["artista"], s["titulo"])
            if k in vistas:
                stats["ya estaban"] += 1; descartes["ya estaban"].append(etiqueta); continue
            vistas.add(k)
            s["bloque"], s["tema"], s["por_genero"] = clasificar(s["generos"], a.tema, a.bloque, a.forzar_tema)
            candidatas.append(s)

    print(f"\nCandidatas nuevas: {len(candidatas)}")
    for motivo, n in stats.items():
        print(f"  descartadas ({motivo}): {n}")
    por_tema = collections.Counter(f"{s['bloque']}/{s['tema']}" for s in candidatas)
    for t, n in sorted(por_tema.items()):
        print(f"  {t}: {n}")
    sin_genero = [s for s in candidatas if not s["por_genero"] and not a.forzar_tema]
    if sin_genero:
        print(f"  ! {len(sin_genero)} sin género reconocible (puesta en {a.bloque or 'metal'}/"
              f"{a.tema or TEMA_POR_BLOQUE[a.bloque or 'metal']}); cámbialas a mano en el JSON si no encajan:")
        for s in sin_genero[:15]:
            print(f"      {s['artista']} - {s['titulo']}  [{s['generos'] or 'sin géneros'}]")
        if len(sin_genero) > 15:
            print(f"      ... y {len(sin_genero) - 15} más")
    if a.dry_run:
        for motivo, lista in descartes.items():
            print(f"\nDescartadas ({motivo}):")
            for e in lista[:20]:
                print("   ", e)
        print("\n--dry-run: no se ha buscado nada ni escrito nada.")
        return 0
    if not candidatas:
        print("Nada que importar.")
        return 0

    # ---- 2. Año, id y YouTube
    flat = full = None
    if not a.sin_yt:
        flat, full = nc.crear_ydl()
    hechas, sin_anio, sin_yt = [], [], []
    try:
        for n, s in enumerate(candidatas, 1):
            r = resolver_anio(s, usar_mb=not a.sin_mb)
            if r is None:
                sin_anio.append(s)
                print(f"[{n}/{len(candidatas)}] {s['artista']} - {s['titulo']}  ->  SIN AÑO, se descarta")
                continue
            anio, revisar, nota = r
            entrada = {"id": f"{siguiente:03d}", "titulo": s["titulo"], "artista": s["artista"], "anio": anio,
                       "bloque": s["bloque"], "tema": s["tema"], "yt": ""}
            siguiente += 1
            if revisar:
                entrada["revisar"] = True
            if nota:
                entrada["nota"] = nota
            if flat is not None:
                try:
                    info = nc.buscar_youtube(flat, full, entrada)
                except Exception as ex:
                    info = None
                    print(f"   ! YouTube: {ex}")
                if info:
                    entrada["yt"] = info["id"]
                    entrada["yt_titulo"] = info.get("title", "")
                    entrada["yt_canal"] = info.get("channel") or info.get("uploader") or ""
                else:
                    sin_yt.append(entrada)
                time.sleep(0.4)
            hechas.append(entrada)
            print(f"[{n}/{len(candidatas)}] {entrada['id']} {entrada['artista']} - {entrada['titulo']}  "
                  f"{anio}{' ?' if revisar else ''}  {entrada['bloque']}/{entrada['tema']}  "
                  f"yt={entrada['yt'] or '-'}{('  (' + entrada.get('yt_canal', '') + ': ' + entrada.get('yt_titulo', '') + ')') if entrada['yt'] else ''}")
    except KeyboardInterrupt:
        print("\nInterrumpido: guardo lo hecho hasta ahora.")

    # ---- 3. Guardar
    nc.guardar_json(destino, existentes + hechas)
    revisar_n = sum(1 for s in hechas if s.get("revisar"))
    print(f"\nGuardadas {len(hechas)} canciones nuevas en {destino} (total {len(existentes) + len(hechas)}).")
    if sin_anio:
        print(f"  Sin año (descartadas): {len(sin_anio)}")
    if revisar_n:
        print(f"  {revisar_n} con año por revisar (campo 'revisar'/'nota'). Comprueba con: python tools/verificar_anios.py --solo-revisar")
    if sin_yt:
        print(f"  {len(sin_yt)} sin vídeo de YouTube: " + ", ".join(s["id"] for s in sin_yt)
              + "  (ponles yt a mano o prueba python tools/resolver_ids.py)")

    # ---- 4. Cartas
    if a.cartas:
        aptas = [s for s in hechas if s["yt"] or a.sin_yt]
        if not aptas:
            print("No hay cartas que generar (ninguna con vídeo).")
        else:
            import generar_cartas as gc
            n, paginas, cols_, filas_ = gc.generar_pdf(aptas, a.base, a.pdf, a.tam)
            print(f"\n{n} cartas -> {a.pdf} ({paginas} páginas, {cols_}x{filas_} por hoja). "
                  "Imprime a doble cara, giro por el borde largo.")
            if len(aptas) < len(hechas):
                print(f"  ({len(hechas) - len(aptas)} sin vídeo no tienen carta todavía.)")
            print("  Recuerda subir el canciones.json actualizado a GitHub ANTES de usar las cartas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
