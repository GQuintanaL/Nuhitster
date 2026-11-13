# Nuhitster

Juego de cartas musical tipo Hitster con **nu metal, metal moderno, gothic rock, post-punk, darkwave y synthpop**. Cada carta lleva un QR: se escanea **dentro de la propia web**, suena la canción (sin ver el título) y los jugadores colocan la carta en su línea temporal según el año.

Todo es estático: funciona en GitHub Pages, sin servidor.

## Contenido

```
index.html              Web: escáner de QR, mazo, filtros por tema, reproductor oculto y "Revelar"
canciones.json          Base de datos de canciones (201 para empezar)
sw.js, manifest.webmanifest, icons/   Hacen que la web se instale como app y abra sin esperar
vendor/jsQR.js          Lector de QR (Apache-2.0) que usa el escáner
ejemplos/               CSV de ejemplo con el formato de Spotify (Exportify)
tools/
  importar_spotify.py   CSV de Spotify -> canciones nuevas + YouTube + años + cartas
  resolver_ids.py       Busca en YouTube cada canción sin enlace y rellena "yt"
  verificar_anios.py    Comprueba los años contra MusicBrainz
  generar_cartas.py     Crea el PDF de cartas con QR (doble cara)
  nuh_common.py         Código compartido por los scripts
  requirements.txt      Dependencias de Python
package.json, capacitor.config.js, android-res/, tools/*.js, .github/workflows/apk.yml
                        Opcional: compilar una app Android (APK) desde GitHub
```

## Puesta en marcha

1. **Sube el repo** `Nuhitster` a GitHub (con `index.html` y `canciones.json` en la raíz) y activa Pages: *Settings → Pages → Deploy from a branch → main / (root)*. La web quedará en `https://TUUSUARIO.github.io/Nuhitster/`.
2. **Instala dependencias** en tu ordenador: `pip install -r tools/requirements.txt`
3. **Rellena los enlaces de YouTube**: `python tools/resolver_ids.py`. Imprime qué vídeo ha elegido para cada canción (canal y título); revísalo por encima. Solo acepta vídeos incrustables. Si alguna sale "SIN RESULTADO" o da error al reproducir, pon el ID del vídeo a mano en el campo `yt`.
4. **Verifica los años**: `python tools/verificar_anios.py --solo-revisar`. Las canciones con `"revisar": true` son las que no estaban 100 % claras. Con `--confirmar` se quita la marca a las que coinciden.
5. **Sube los cambios** de `canciones.json` a GitHub.
6. **Genera las cartas**: `python tools/generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --solo-con-yt`

Imprime a doble cara con giro por el borde largo (12 cartas de 60 mm por hoja A4).

## Jugar: escáner dentro de la web

1. Abre la web en el móvil y pulsa **Escanear carta** (la primera vez el navegador pide permiso de cámara; hace falta https, y GitHub Pages lo es).
2. Apunta al QR: la carta se abre y **la canción empieza sola**. Se coloca la carta en la línea y se pulsa **Revelar** para ver año, título y artista.
3. **Escanear otra carta** vuelve al escáner sin pasar por ningún sitio más. Si la cámara no va, hay una casilla para escribir el número de la carta.

Funciona igual con la cámara normal del móvil: el QR es un enlace a la web (`…/?id=042`).

**Instalarla como app** (sin APK): en Chrome para Android, menú ⋮ → *Instalar aplicación*; en iPhone, Safari → Compartir → *Añadir a pantalla de inicio*. Se abre a pantalla completa, con su icono, y la parte de la app carga sin conexión (la música sigue necesitando internet porque viene de YouTube).

Notas:
- Si el navegador bloquea el inicio automático de la música (pasa sobre todo en iPhone), pulsa ▶ una vez.
- Si se apaga la pantalla, la música se pausa: ajusta el tiempo de bloqueo en las partidas.
- Cuando cambies `index.html`, sube el número de `CACHE` en `sw.js` (`nuhitster-v1` → `v2`) para que los móviles se actualicen.
- `?admin` muestra la lista completa (con spoilers) y qué canciones aún no tienen enlace.

## Importar canciones desde Spotify

1. Entra en [exportify.net](https://exportify.net), inicia sesión con Spotify y exporta una lista (o *Liked Songs*) a CSV. Vale cualquier CSV con título y artista; las columnas se detectan solas (`Track Name`, `Artist Name(s)`, `Release Date`, `Genres`…).
2. **Vista previa** (sin red, no escribe nada): `python tools/importar_spotify.py mi_lista.csv --dry-run`. Muestra qué entra, qué se descarta (directos y canciones que ya están) y cómo se clasifica. Prueba primero con `ejemplos/spotify_ejemplo.csv`.
3. **Importar** y generar las cartas nuevas:
   `python tools/importar_spotify.py mi_lista.csv --cartas --base https://TUUSUARIO.github.io/Nuhitster/`
4. **Sube `canciones.json` a GitHub antes de usar las cartas** y revisa las canciones con `"revisar": true` (llevan una `nota` con lo que pasó).

Qué hace con cada canción:
- Limpia el título (`- Remastered 2011`, `(Mono)`…) y descarta directos y repetidas.
- Clasifica en bloque y tema por los géneros de Spotify. Si no hay género reconocible usa `--bloque`/`--tema` (o `--forzar-tema` para toda la lista) y te lo avisa.
- **Año**: Spotify da el del álbum, que en remasterizaciones y recopilatorios sale mal. Se compara con MusicBrainz y se usa el más antiguo; si difieren 2 años o más, o solo hay una fuente, queda marcada para revisar. Con `--sin-mb` se omite la comprobación.
- Busca en YouTube un vídeo incrustable (`--sin-yt` para omitirlo). Las canciones sin vídeo no generan carta hasta que les pongas `yt`.
- Los ids nuevos empiezan en 300 y no se reutilizan. Con `--salida otro.json` no toca tu `canciones.json`.

## App Android (APK) — opcional

La web instalada ya hace de app. Si prefieres un APK de verdad, el repo incluye un envoltorio (Capacitor) que **compila GitHub**, sin instalar nada en tu ordenador:

1. En GitHub: pestaña **Actions → Compilar APK → Run workflow**. (Opcional: escribe la URL de tu web; por defecto usa la de GitHub Pages de este repo.)
2. Al terminar (unos minutos), descarga `Nuhitster-apk` de *Artifacts*. Si subes una etiqueta que empiece por `v` (p. ej. `v1.0.0`), también se publica en *Releases*.
3. Pásalo al móvil e instálalo (Android pedirá permitir instalar apps de este origen). Es un APK de depuración, válido para uso propio.

El APK lleva la web dentro y, con conexión, baja de tu web la lista de canciones más reciente, así que **no hace falta recompilar al añadir canciones**. Lleva el permiso de cámara para el escáner.

Importante: **el APK no se ha podido compilar donde se preparó** (sin acceso a los repositorios de Android), así que el primer *Run workflow* es la primera prueba real. El proyecto sí se genera correctamente (permiso de cámara, iconos y web incluidos). Si YouTube dijera "error de reproducción" dentro de la app, vuelve a ejecutar el workflow marcando **modo_remoto**: la app carga entonces tu web en vivo, con su dirección real.

## Reglas del año

El año es el de la **primera publicación** (álbum o single, lo que saliera antes), no el de remasterizaciones ni recopilatorios.

## Añadir canciones a mano

Añade una entrada al final de `canciones.json` con un **id nuevo** (no reutilices ids: están impresos en los QR):

```json
{"id":"400","titulo":"Título","artista":"Banda","anio":2004,"bloque":"metal","tema":"nu-metal","yt":""}
```

- `bloque`: `metal` o `gotico`
- `tema`: `nu-metal`, `alt-metal`, `metalcore`, `metal-moderno`, `industrial`, `gothic-rock`, `post-punk`, `darkwave`, `synthpop`, `gothic-metal`
- `yt`: ID del vídeo de YouTube (lo rellena `resolver_ids.py`)
- `inicio` (opcional): segundo desde el que empieza a sonar
- `revisar` (opcional): `true` si no estás seguro del año

Si añades un tema nuevo, añádelo también a `TEMAS` en `index.html` y en `tools/nuh_common.py` (y, si quieres que el importador lo reconozca por género, a `REGLAS` en `tools/importar_spotify.py`).

## Notas

- "Hitster" es una marca registrada: si algún día lo publicas, mantén nombre y diseño propios (por eso "Nuhitster").
- La web no aloja audio: reproduce vídeos de YouTube incrustados, que pueden dejar de estar disponibles. Si una carta falla, cambia su `yt`.
- La tapa sobre el vídeo oculta el título mientras suena; al pulsar "Revelar" se muestra el año y los datos.
