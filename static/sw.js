/* Service worker de weblife: lo que hace que la web se pueda instalar como app.
   - Las páginas siempre se piden a internet: así ves tus datos al día y cada
     cambio que subas (git pull + Reload) aparece al momento.
   - El CSS, el JS y las imágenes (enlaces con "?v=...") se guardan en el móvil
     la primera vez y luego salen de ahí al instante. Cuando cambias un archivo,
     su "?v=" cambia y se descarga el nuevo.
   - Sin internet se enseña la página "Sin conexión". */
const CACHE = "weblife-v4";   // súbelo si cambias sin-conexion.html o los iconos
const ESTATICOS = "weblife-estaticos";
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
    return Promise.all(nombres.filter(function (n) { return n !== CACHE && n !== ESTATICOS; })
                              .map(function (n) { return caches.delete(n); }));
  }).then(function () { return self.clients.claim(); }));
});

// CSS/JS/imágenes con versión: primero el móvil; si no está, internet (y se guarda)
function desdeElMovil(peticion, url) {
  return caches.open(ESTATICOS).then(function (cache) {
    return cache.match(peticion).then(function (guardado) {
      if (guardado) return guardado;
      return fetch(peticion).then(function (respuesta) {
        if (respuesta.ok) {
          // Quitamos versiones viejas del mismo archivo para no llenar el móvil
          cache.keys().then(function (claves) {
            claves.forEach(function (c) {
              if (new URL(c.url).pathname === url.pathname && c.url !== peticion.url) cache.delete(c);
            });
          });
          cache.put(peticion, respuesta.clone());
        }
        return respuesta;
      });
    });
  });
}

self.addEventListener("fetch", function (e) {
  // Solo intervenimos al pedir cosas (GET). Formularios, subidas y lo demás van directos.
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(function () {
      return caches.match(SIN_CONEXION);
    }));
  } else if (url.origin === location.origin && url.pathname.startsWith("/static/") && url.searchParams.has("v")) {
    e.respondWith(desdeElMovil(e.request, url));
  } else if (url.pathname === "/static/iconos/icono-192.png") {
    // El icono de la página "Sin conexión": de internet si hay, si no de la caché
    e.respondWith(fetch(e.request).catch(function () { return caches.match(e.request); }));
  }
});
