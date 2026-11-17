/* Service worker de weblife: lo que hace que la web se pueda instalar como app.
   A propósito NO guarda páginas ni CSS/JS en caché: así cada cambio que subas
   (git pull + Reload) aparece al momento en la app, sin versiones viejas.
   Solo guarda la página "Sin conexión" para enseñarla si no hay internet. */
const CACHE = "weblife-v2";   // súbelo si cambias los iconos
const SIN_CONEXION = "/static/sin-conexion.html";

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return c.addAll([SIN_CONEXION, "/static/iconos/icono-192.png"]);
  }));
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  // Borra cachés de versiones anteriores de este archivo
  e.waitUntil(caches.keys().then(function (nombres) {
    return Promise.all(nombres.filter(function (n) { return n !== CACHE; })
                              .map(function (n) { return caches.delete(n); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  // Solo intervenimos al abrir una página (GET). Formularios, subidas y lo demás van directos.
  if (e.request.method !== "GET") return;
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(function () {
      return caches.match(SIN_CONEXION);
    }));
  } else if (new URL(e.request.url).pathname === "/static/iconos/icono-192.png") {
    // El icono de la página "Sin conexión": de internet si hay, si no de la caché
    e.respondWith(fetch(e.request).catch(function () { return caches.match(e.request); }));
  }
});
