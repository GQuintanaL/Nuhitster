#!/usr/bin/env python3
"""
Genera un PDF A4 con las cartas de Nuhitster, listo para imprimir a doble cara.

Cada carta es un cuadrado de 60 mm:
  - Cara A: QR que abre la canción en tu web (sin revelar nada).
  - Cara B: año, título, artista y tema.

Las páginas se alternan (cara A, cara B, cara A, cara B...). Imprime a doble cara
con el giro por el BORDE LARGO. Las caras B ya van en espejo para que casen.

Ejemplos:
  python generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/
  python generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --bloque gotico
  python generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --tema nu-metal --tema metalcore
  python generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --solo-con-yt
  python generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --ids 300,301,302
"""
import argparse
import io
import sys

import nuh_common as nc

try:
    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader, simpleSplit
    from reportlab.pdfgen import canvas
except ImportError:
    sys.exit("Faltan dependencias. Ejecuta:  pip install -r tools/requirements.txt")

COLORES = {"metal": (0.85, 0.15, 0.12), "gotico": (0.55, 0.35, 0.85)}


def qr_reader(url):
    img = qrcode.make(url, error_correction=qrcode.constants.ERROR_CORRECT_M, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def marco(c, x, y, size):
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.3)
    c.rect(x, y, size, size)


def cara_qr(c, x, y, size, s, url):
    marco(c, x, y, size)
    col = COLORES.get(s["bloque"], (0.3, 0.3, 0.3))
    band = 8 * mm
    c.setFillColorRGB(*col)
    c.rect(x, y, size, band, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + size / 2, y + band / 2 - 2.4, f"NUHITSTER  ·  {s['id']}")
    qr = size - 2 * 5 * mm - band + 2 * mm
    c.drawImage(qr_reader(url), x + (size - qr) / 2, y + band + 2 * mm, qr, qr)


def cara_datos(c, x, y, size, s):
    marco(c, x, y, size)
    col = COLORES.get(s["bloque"], (0.3, 0.3, 0.3))
    band = 6 * mm
    c.setFillColorRGB(*col)
    c.rect(x, y + size - band, size, band, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(x + size / 2, y + size - band / 2 - 2.2,
                        nc.TEMAS.get(s["tema"], s["tema"].upper()))

    c.setFillColorRGB(0.08, 0.08, 0.1)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(x + size / 2, y + size * 0.52, str(s["anio"]))

    ancho = size - 8 * mm
    fs = 9.5
    while fs >= 6:
        lineas = simpleSplit(s["titulo"], "Helvetica-Bold", fs, ancho)
        if len(lineas) <= 3:
            break
        fs -= 0.5
    c.setFont("Helvetica-Bold", fs)
    ty = y + size * 0.36
    for ln in lineas:
        c.drawCentredString(x + size / 2, ty, ln)
        ty -= fs + 1.5

    c.setFillColorRGB(0.35, 0.35, 0.4)
    fa = 8
    while fa >= 5:
        lin_a = simpleSplit(s["artista"], "Helvetica", fa, ancho)
        if len(lin_a) <= 2:
            break
        fa -= 0.5
    c.setFont("Helvetica", fa)
    ty -= 2
    for ln in lin_a:
        c.drawCentredString(x + size / 2, ty, ln)
        ty -= fa + 1.5

    c.setFillColorRGB(0.6, 0.6, 0.65)
    c.setFont("Helvetica", 6)
    c.drawCentredString(x + size / 2, y + 3 * mm, s["id"])


def generar_pdf(canciones, base, salida, tam=60):
    """Crea el PDF de cartas. Devuelve (cartas, páginas, columnas, filas)."""
    base = base.rstrip("/")
    canciones = sorted(canciones, key=lambda s: (len(s["id"]), s["id"]))
    size = tam * mm
    W, H = A4
    cols = int(W // size)
    rows = int(H // size)
    por_pagina = cols * rows
    x0 = (W - cols * size) / 2
    y0 = (H - rows * size) / 2

    c = canvas.Canvas(str(salida), pagesize=A4)
    c.setTitle("Nuhitster - cartas")
    for ini in range(0, len(canciones), por_pagina):
        lote = canciones[ini:ini + por_pagina]
        # Cara A (QR)
        for i, s in enumerate(lote):
            r, col = divmod(i, cols)
            x = x0 + col * size
            y = H - y0 - (r + 1) * size
            cara_qr(c, x, y, size, s, f"{base}/?id={s['id']}")
        c.showPage()
        # Cara B (datos), en espejo horizontal para giro por borde largo
        for i, s in enumerate(lote):
            r, col = divmod(i, cols)
            x = x0 + (cols - 1 - col) * size
            y = H - y0 - (r + 1) * size
            cara_datos(c, x, y, size, s)
        c.showPage()
    c.save()
    paginas = 2 * ((len(canciones) + por_pagina - 1) // por_pagina)
    return len(canciones), paginas, cols, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera el PDF de cartas de Nuhitster")
    ap.add_argument("--base", required=True,
                    help="URL pública de tu web, p. ej. https://usuario.github.io/Nuhitster/")
    ap.add_argument("--json", default=str(nc.JSON_POR_DEFECTO))
    ap.add_argument("--salida", default="nuhitster_cartas.pdf")
    ap.add_argument("--bloque", choices=["metal", "gotico"], help="Solo un bloque")
    ap.add_argument("--tema", action="append", help="Solo estos temas (repetible)")
    ap.add_argument("--ids", help="Solo estos ids, separados por comas (p. ej. 300,301)")
    ap.add_argument("--solo-con-yt", action="store_true", help="Solo canciones que ya tienen enlace de YouTube")
    ap.add_argument("--tam", type=float, default=60, help="Lado de la carta en mm (por defecto 60)")
    a = ap.parse_args(argv)

    canciones = nc.leer_json(a.json)
    if a.bloque:
        canciones = [s for s in canciones if s["bloque"] == a.bloque]
    if a.tema:
        canciones = [s for s in canciones if s["tema"] in a.tema]
    if a.ids:
        ids = {i.strip() for i in a.ids.split(",")}
        canciones = [s for s in canciones if s["id"] in ids]
    if a.solo_con_yt:
        canciones = [s for s in canciones if s.get("yt")]
    if not canciones:
        sys.exit("No hay canciones con esos filtros.")

    n, paginas, cols, rows = generar_pdf(canciones, a.base, a.salida, a.tam)
    print(f"{n} cartas -> {a.salida} ({paginas} páginas, {cols}x{rows} por hoja)")
    print("Imprime a doble cara, giro por el borde largo. Ejemplo de QR:",
          f"{a.base.rstrip('/')}/?id={sorted(canciones, key=lambda s: (len(s['id']), s['id']))[0]['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
