#!/usr/bin/env python3
"""Funciones compartidas por los scripts de Nuhitster (no se ejecuta solo)."""
import json
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JSON_POR_DEFECTO = RAIZ / "canciones.json"

TEMAS = {
    "nu-metal": "NU METAL", "alt-metal": "ALT METAL", "metalcore": "METALCORE",
    "metal-moderno": "METAL MODERNO", "industrial": "INDUSTRIAL",
    "gothic-rock": "GOTHIC ROCK", "post-punk": "POST-PUNK", "darkwave": "DARKWAVE",
    "synthpop": "SYNTHPOP", "gothic-metal": "GOTHIC METAL",
}
# "industrial" no tiene bloque fijo: hay industrial de metal (Rammstein) y de gótico (Front 242).
BLOQUE_DE_TEMA = {
    "nu-metal": "metal", "alt-metal": "metal", "metalcore": "metal", "metal-moderno": "metal",
    "gothic-rock": "gotico", "post-punk": "gotico", "darkwave": "gotico",
    "synthpop": "gotico", "gothic-metal": "gotico",
}


# ---------------------------------------------------------------- JSON
def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


_copias_hechas = set()


def guardar_json(ruta, canciones):
    """Guarda una canción por línea (diffs limpios en git). Hace copia .bak la primera vez."""
    ruta = Path(ruta)
    if ruta.exists() and str(ruta) not in _copias_hechas:
        shutil.copy(ruta, str(ruta) + ".bak")
        _copias_hechas.add(str(ruta))
    cuerpo = ",\n".join(json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in canciones)
    tmp = Path(str(ruta) + ".tmp")
    tmp.write_text("[\n" + cuerpo + "\n]\n", encoding="utf-8")
    os.replace(tmp, ruta)


# ---------------------------------------------------------------- Texto
def quitar_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t)) if not unicodedata.combining(c))


def norm(t):
    """Forma comparable de un título o artista: sin acentos, sin paréntesis, sin 'the'."""
    t = quitar_acentos(t).lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = t.replace("&", " and ")
    t = re.sub(r"[^\w\s]|_", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^the ", "", t)


_RUIDO_GUION = re.compile(
    r"\s[-–—]\s.*\b(re-?master(?:ed)?|mono|stereo|bonus track|single version|radio edit|album version|deluxe|expanded)\b.*$",
    re.I)
_RUIDO_PAREN = re.compile(
    r"\s*[\(\[][^)\]]*\b(re-?master(?:ed)?|mono|stereo|bonus track|deluxe|expanded|anniversary)\b[^)\]]*[\)\]]",
    re.I)
_EN_VIVO = re.compile(r"[-–—(\[]\s*live\b|\blive\s+(?:at|from)\b|\bunplugged\b|\ben vivo\b", re.I)


def limpiar_titulo(t):
    """Quita 'Remastered', '2011 Remaster', 'Mono Version', etc. de un título de Spotify."""
    t = _RUIDO_GUION.sub("", str(t))
    t = _RUIDO_PAREN.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def es_directo(t):
    return bool(_EN_VIVO.search(str(t)))


def clave(artista, titulo):
    """Clave para detectar canciones repetidas."""
    return norm(artista) + "|" + norm(limpiar_titulo(titulo))


# ---------------------------------------------------------------- MusicBrainz
UA = "Nuhitster/1.0 (proyecto personal de juego musical)"


def consulta_mb(titulo, artista):
    esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
    q = f'recording:"{esc(titulo)}" AND artist:"{esc(artista)}"'
    url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode({"query": q, "fmt": "json", "limit": 25})
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("recordings", [])
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and intento < 2:
                time.sleep(2 * (intento + 1))
                continue
            raise
    return []


# Grabaciones alternativas (demos, directos, mezclas) que pueden tener fecha anterior al original.
_VARIANTE = re.compile(r"\b(live|demo|acoustic|remix|mix|version|session|instrumental|unplugged|edit|rehearsal|take|karaoke)\b", re.I)


def anio_musicbrainz(titulo, artista):
    """Año de primera publicación según MusicBrainz, o None si no hay coincidencia clara."""
    limpio = limpiar_titulo(titulo)
    t_norm, a_norm = norm(limpio), norm(artista)
    if not t_norm or not a_norm:
        return None
    anios = []
    for rec in consulta_mb(limpio, artista):
        fecha = rec.get("first-release-date") or ""
        if not re.match(r"^\d{4}", fecha):
            continue
        if _VARIANTE.search(rec.get("title", "")) and not _VARIANTE.search(limpio):
            continue
        credito = norm(" ".join(c.get("name", "") for c in rec.get("artist-credit", []) if isinstance(c, dict)))
        if norm(rec.get("title", "")) == t_norm and credito and (a_norm in credito or credito in a_norm):
            anios.append(int(fecha[:4]))
    return min(anios) if anios else None


# ---------------------------------------------------------------- YouTube
MALOS = ("live", "en vivo", "cover", "karaoke", "reaction", "tutorial", "lesson", "remix",
         "8d", "slowed", "sped up", "nightcore", "tribute", "parody", "how to play",
         "drum cam", "guitar cover", "bass cover", "piano cover")


def crear_ydl():
    try:
        import yt_dlp
    except ImportError:
        sys.exit("Falta yt-dlp. Ejecuta:  pip install yt-dlp")
    base = {"quiet": True, "no_warnings": True, "skip_download": True}
    return yt_dlp.YoutubeDL({**base, "extract_flat": True}), yt_dlp.YoutubeDL(base)


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
        patron = r"\b" + re.escape(mal) + r"\b"
        if re.search(patron, titulo) and not re.search(patron, original):
            return False
    dur = e.get("duration")
    if dur is not None and not (60 <= dur <= 1200):
        return False
    return True


def buscar_youtube(flat, full, s):
    """Devuelve la info del mejor vídeo incrustable para la canción, o None."""
    q = f"{s['artista']} {s['titulo']} official audio"
    res = flat.extract_info(f"ytsearch8:{q}", download=False)
    entradas = [e for e in (res.get("entries") or []) if e and candidato_valido(e, s)]
    entradas.sort(key=lambda e: -puntuar(e, s))  # orden estable: a igual puntuación manda YouTube
    for e in entradas[:5]:
        try:
            info = full.extract_info(f"https://www.youtube.com/watch?v={e['id']}", download=False)
        except Exception:
            continue
        if info.get("playable_in_embed") is False or info.get("availability") not in (None, "public", "unlisted"):
            continue
        return info
    return None
