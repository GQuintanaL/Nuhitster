// Ajusta el proyecto Android que genera "cap add android":
//  1. Declara el permiso de cámara (para el escáner de QR).
//  2. Sustituye iconos y pantalla de arranque por los de Nuhitster (carpeta android-res/).
//  3. Fondo oscuro en el arranque y en el icono adaptativo.
const fs = require("fs");
const path = require("path");

const raiz = path.resolve(__dirname, "..");
const res = path.join(raiz, "android/app/src/main/res");
const manifiesto = path.join(raiz, "android/app/src/main/AndroidManifest.xml");

function reemplazar(archivo, desde, hacia, etiqueta) {
  const txt = fs.readFileSync(archivo, "utf8");
  if (!txt.includes(desde)) throw new Error(`No encuentro "${etiqueta}" en ${archivo}; ¿cambió la plantilla de Capacitor?`);
  fs.writeFileSync(archivo, txt.replace(desde, hacia));
}

// 1. Permisos de cámara
let m = fs.readFileSync(manifiesto, "utf8");
if (!m.includes("android.permission.CAMERA")) {
  m = m.replace(
    '<uses-permission android:name="android.permission.INTERNET" />',
    '<uses-permission android:name="android.permission.INTERNET" />\n' +
    '    <uses-permission android:name="android.permission.CAMERA" />\n' +
    '    <uses-feature android:name="android.hardware.camera" android:required="false" />\n' +
    '    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />'
  );
  if (!m.includes("android.permission.CAMERA")) throw new Error("No se pudo añadir el permiso CAMERA al manifiesto");
  fs.writeFileSync(manifiesto, m);
}

// 2. Iconos y pantalla de arranque
fs.cpSync(path.join(raiz, "android-res"), res, { recursive: true, force: true });

// 3. Colores de fondo
fs.writeFileSync(
  path.join(res, "values/ic_launcher_background.xml"),
  '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#0B0A0F</color>\n</resources>\n'
);
const estilos = path.join(res, "values/styles.xml");
if (!fs.readFileSync(estilos, "utf8").includes("windowSplashScreenBackground")) {
  reemplazar(
    estilos,
    '<item name="android:background">@drawable/splash</item>',
    '<item name="android:background">@drawable/splash</item>\n        <item name="windowSplashScreenBackground">#0B0A0F</item>',
    "fondo de arranque"
  );
}
console.log("Android parcheado: permiso de cámara, iconos y arranque.");
