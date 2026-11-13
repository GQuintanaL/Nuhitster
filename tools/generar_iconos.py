#!/usr/bin/env python3
"""
Genera los iconos de Nuhitster (ecualizador de 5 barras con degradado rojo-morado):
  - icons/            iconos de la web / PWA
  - android-res/      iconos y pantalla de arranque de la app Android (los copia tools/patch-android.js)

Para cambiar el diseño, edita ALTURAS / colores y vuelve a ejecutar:
  python tools/generar_iconos.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
ROJO, MORADO, FONDO = (255, 59, 48), (166, 107, 255), (11, 10, 15)
ALTURAS = [0.42, 0.78, 1.0, 0.64, 0.5]


def mezcla(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def barras(lado, zona_util, fondo=FONDO):
    """Cuadrado 'lado' con las barras ocupando 'zona_util' (0-1) del lienzo. fondo=None -> transparente."""
    S = lado * 4  # supermuestreo para bordes suaves
    degradado = Image.new("RGB", (S, S))
    px = degradado.load()
    for y in range(S):
        c = mezcla(MORADO, ROJO, y / (S - 1))
        for x in range(S):
            px[x, y] = c
    mascara = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mascara)
    zona = S * zona_util
    x0 = (S - zona) / 2
    ancho = zona / (len(ALTURAS) * 1.6 - 0.6)
    hueco = ancho * 0.6
    base = (S + zona) / 2
    for i, a in enumerate(ALTURAS):
        x = x0 + i * (ancho + hueco)
        d.rounded_rectangle([x, base - zona * a, x + ancho, base], radius=ancho / 2, fill=255)
    lienzo = Image.new("RGBA", (S, S), (0, 0, 0, 0) if fondo is None else fondo + (255,))
    lienzo.paste(degradado, (0, 0), mascara)
    return lienzo.resize((lado, lado), Image.LANCZOS)


def redondo(img):
    m = Image.new("L", (img.width * 4, img.height * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, m.width - 1, m.height - 1], fill=255)
    m = m.resize(img.size, Image.LANCZOS)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), m)
    return out


def splash(w, h):
    img = Image.new("RGBA", (w, h), FONDO + (255,))
    lado = int(min(w, h) * 0.34)
    ic = barras(lado, 0.8, fondo=None)
    img.paste(ic, ((w - lado) // 2, (h - lado) // 2), ic)
    return img.convert("RGB")


def guardar(img, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    img.save(ruta, optimize=True)


def main():
    # Web
    guardar(barras(192, 0.62).convert("RGB"), RAIZ / "icons/icon-192.png")
    guardar(barras(512, 0.62).convert("RGB"), RAIZ / "icons/icon-512.png")
    guardar(barras(512, 0.50).convert("RGB"), RAIZ / "icons/icon-maskable-512.png")

    # Android
    res = RAIZ / "android-res"
    legado = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
    primer_plano = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
    pantalla = {"mdpi": (320, 480), "hdpi": (480, 800), "xhdpi": (720, 1280),
                "xxhdpi": (960, 1600), "xxxhdpi": (1280, 1920)}
    for dens in legado:
        base = barras(legado[dens], 0.62)
        guardar(base, res / f"mipmap-{dens}/ic_launcher.png")
        guardar(redondo(base), res / f"mipmap-{dens}/ic_launcher_round.png")
        # Adaptativo: la zona segura es el 61 % central del lienzo de 108 dp
        guardar(barras(primer_plano[dens], 0.5, fondo=None), res / f"mipmap-{dens}/ic_launcher_foreground.png")
        w, h = pantalla[dens]
        guardar(splash(w, h), res / f"drawable-port-{dens}/splash.png")
        guardar(splash(h, w), res / f"drawable-land-{dens}/splash.png")
    guardar(splash(480, 320), res / "drawable/splash.png")
    print("Iconos generados en icons/ y android-res/")


if __name__ == "__main__":
    main()
