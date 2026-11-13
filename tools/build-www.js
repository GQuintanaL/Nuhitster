// Copia los archivos de la web a www/, que es lo que empaqueta la app Android.
// Si NUH_WEB está definida (https://usuario.github.io/Nuhitster/), la app bajará de ahí la lista
// de canciones actualizada al abrir (y usará la copia incluida si no hay conexión).
const fs = require("fs");
const path = require("path");

const raiz = path.resolve(__dirname, "..");
const salida = path.join(raiz, "www");

fs.rmSync(salida, { recursive: true, force: true });
fs.mkdirSync(salida, { recursive: true });

for (const f of ["index.html", "canciones.json", "config.js", "manifest.webmanifest", "vendor", "icons"]) {
  fs.cpSync(path.join(raiz, f), path.join(salida, f), { recursive: true });
}

const web = (process.env.NUH_WEB || "").trim();
if (web) {
  if (!/^https:\/\/[^\s"'<>]+$/.test(web)) {
    console.warn(`NUH_WEB no parece una URL https válida (${web}); se ignora.`);
  } else {
    const base = web.endsWith("/") ? web : web + "/";
    const cfg = { jsonUrl: base + "canciones.json" };
    fs.writeFileSync(path.join(salida, "config.js"), "window.NUH_CONFIG = " + JSON.stringify(cfg) + ";\n");
    console.log("Actualización de canciones desde:", cfg.jsonUrl);
  }
}
console.log("www/ listo:", fs.readdirSync(salida).join(", "));
