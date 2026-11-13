// Configuración de la app Android.
// Por defecto la app lleva dentro index.html, canciones.json y el escáner (abre al instante).
// Si NUH_URL está definida (https://usuario.github.io/Nuhitster/), la app carga esa web en vivo
// en lugar de los archivos incluidos: útil si YouTube rechazara los vídeos dentro de la app.
const remota = (process.env.NUH_URL || "").trim();

module.exports = {
  appId: "com.nuhitster.app",
  appName: "Nuhitster",
  webDir: "www",
  backgroundColor: "#0b0a0f",
  server: remota
    ? { url: remota, cleartext: false }
    : { androidScheme: "https" }
};
