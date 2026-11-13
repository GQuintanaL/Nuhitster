/* Service worker de Nuhitster.
   - La "carcasa" de la app (HTML, escáner, iconos) se guarda para abrir sin esperar a la red.
   - canciones.json va primero a la red (para recibir canciones nuevas) y cae a la copia guardada.
   - La música sigue necesitando conexión: viene de YouTube.
   Cambia CACHE (v1 -> v2...) cuando modifiques index.html para forzar la actualización. */
const CACHE = "nuhitster-v1";
const SHELL = [
  "./",
  "index.html",
  "canciones.json",
  "config.js",
  "vendor/jsQR.js",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function redPrimero(req, claveFallback) {
  try {
    const res = await fetch(req);
    if (res && res.ok) {
      const copia = res.clone();
      caches.open(CACHE).then(c => c.put(claveFallback || req, copia));
    }
    return res;
  } catch (err) {
    const guardado = await caches.match(claveFallback || req, { ignoreSearch: !!claveFallback });
    if (guardado) return guardado;
    throw err;
  }
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // YouTube y demás: directos a la red

  // Abrir la app (con o sin ?id=...): siempre la misma página
  if (req.mode === "navigate") {
    e.respondWith(redPrimero(new Request("index.html"), "index.html").catch(() => caches.match("index.html")));
    return;
  }
  // La lista de canciones: red primero
  if (url.pathname.endsWith("/canciones.json")) {
    e.respondWith(redPrimero(req));
    return;
  }
  // Resto de archivos propios: copia guardada primero
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res && res.ok) {
        const copia = res.clone();
        caches.open(CACHE).then(c => c.put(req, copia));
      }
      return res;
    }))
  );
});
