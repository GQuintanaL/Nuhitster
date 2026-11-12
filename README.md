# Nuhitster

Juego de cartas musical tipo Hitster con **nu metal, metal moderno, gothic rock, post-punk, darkwave y synthpop**. Se sacan cartas con un QR, suena la canción (sin ver el título) y los jugadores colocan la carta en su línea temporal según el año.

Todo es estático: funciona en GitHub Pages sin servidor.

## Contenido

```
index.html            Web: mazo, filtros por tema, reproductor oculto y botón "Revelar"
canciones.json        Base de datos de canciones (201 para empezar)
tools/
  resolver_ids.py     Busca en YouTube cada canción y rellena el campo "yt"
  verificar_anios.py  Comprueba los años contra MusicBrainz
  generar_cartas.py   Crea el PDF de cartas con QR (doble cara)
  requirements.txt    Dependencias de los scripts
```

## Puesta en marcha

1. **Sube el repo** `Nuhitster` a GitHub (con `index.html` y `canciones.json` en la raíz) y activa Pages: *Settings → Pages → Deploy from a branch → main / (root)*. La web quedará en `https://TUUSUARIO.github.io/Nuhitster/`.
2. **Instala dependencias** en tu ordenador: `pip install -r tools/requirements.txt`
3. **Rellena los enlaces de YouTube**: `python tools/resolver_ids.py`. Imprime qué vídeo ha elegido para cada canción (canal y título); revísalo por encima. Solo acepta vídeos incrustables. Si alguna sale "SIN RESULTADO" o da error al reproducir, pon el ID del vídeo a mano en el campo `yt`.
4. **Verifica los años**: `python tools/verificar_anios.py --solo-revisar`. Las canciones marcadas con `"revisar": true` son las que no tenía 100 % claras. Con `--confirmar` se quita la marca a las que coinciden.
5. **Sube los cambios** de `canciones.json` a GitHub.
6. **Genera las cartas**: `python tools/generar_cartas.py --base https://TUUSUARIO.github.io/Nuhitster/ --solo-con-yt`

Imprime a doble cara con giro por el borde largo (12 cartas de 60 mm por hoja A4).

## Cómo se juega

- **Con cartas**: escanea el QR de una carta; la web abre y reproduce esa canción. Se coloca en la línea temporal de quien juega y después se da la vuelta a la carta (o se pulsa "Revelar") para ver el año.
- **Sin cartas**: en la página de inicio elige mazo (todo, metal, gótico) y temas, y pulsa "Sacar carta". No repite hasta agotar el mazo.
- `?admin` muestra la lista completa (con spoilers) y qué canciones aún no tienen enlace.

## Reglas del año

El año es el de la **primera publicación** (álbum o single, lo que saliera antes), no el de remasterizaciones ni recopilatorios.

## Añadir canciones

Añade una entrada al final de `canciones.json` con un **id nuevo** (no reutilices ids: están impresos en los QR):

```json
{"id":"300","titulo":"Título","artista":"Banda","anio":2004,"bloque":"metal","tema":"nu-metal","yt":""}
```

- `bloque`: `metal` o `gotico`
- `tema`: `nu-metal`, `alt-metal`, `metalcore`, `metal-moderno`, `industrial`, `gothic-rock`, `post-punk`, `darkwave`, `synthpop`, `gothic-metal`
- `yt`: ID del vídeo de YouTube (lo rellena `resolver_ids.py`)
- `inicio` (opcional): segundo desde el que empieza a sonar
- `revisar` (opcional): `true` si no estás seguro del año

Si añades un tema nuevo, añádelo también a `TEMAS` en `index.html` y en `tools/generar_cartas.py`.

## Notas

- "Hitster" es una marca registrada: si algún día lo publicas, mantén nombre y diseño propios (por eso "Nuhitster").
- La web no aloja audio: reproduce vídeos de YouTube incrustados, que pueden dejar de estar disponibles. Si una carta falla, cambia su `yt`.
- La tapa negra sobre el vídeo oculta el título mientras suena; al pulsar "Revelar" se muestra el vídeo.
