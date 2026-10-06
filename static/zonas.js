// ============================================================
//  zonas.js - Actualizar solo la casilla que tocas
//
//  Las partes que se pueden actualizar solas llevan data-zona="nombre"
//  (una tarea, una clase del panel del horario, un día del calendario).
//  Al enviar un formulario que está dentro de una zona, lo mandamos sin
//  recargar, pedimos la página otra vez y cambiamos solo esa zona.
//  Si la zona ya no existe (por ejemplo, borraste la tarea), se quita.
//  Si algo falla, el formulario se envía normal, como siempre.
// ============================================================

(function () {
  "use strict";
  if (!window.fetch || !window.DOMParser) return;

  // Mensaje pequeño abajo (por ejemplo "Tarea guardada.")
  var aviso = null, temporizador = null;
  function mostrarAviso(texto) {
    if (!texto) return;
    if (!aviso) {
      aviso = document.createElement("div");
      aviso.className = "aviso-flotante vidrio";
      aviso.setAttribute("role", "status");
      document.body.appendChild(aviso);
    }
    aviso.textContent = "✓ " + texto;
    aviso.classList.add("visible");
    clearTimeout(temporizador);
    temporizador = setTimeout(function () { aviso.classList.remove("visible"); }, 2500);
  }

  // Todas las zonas con ese nombre (una tarea puede salir en Tareas y en Pendientes a la vez)
  function zonasLlamadas(raiz, nombre) {
    return Array.prototype.filter.call(raiz.querySelectorAll("[data-zona]"), function (z) {
      return z.dataset.zona === nombre;
    });
  }
  function buscarZona(raiz, nombre) { return zonasLlamadas(raiz, nombre)[0] || null; }

  // Dirección de la página donde está la zona (con el scroll continuo puede ser otra)
  function urlDeLaPagina(zona) {
    var tramo = zona.closest(".tramo");
    if (!tramo || tramo.classList.contains("actual") || !tramo.dataset.url) return location.href;
    return location.origin + tramo.dataset.url;
  }

  function pedirPagina(url) {
    return fetch(url, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok || r.redirected) throw new Error("sin página");
      return r.text();
    });
  }

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (e.defaultPrevented || (form.method || "").toLowerCase() !== "post") return;
    var zona = form.closest("[data-zona]");
    if (!zona) return;   // fuera de una zona: se envía normal
    e.preventDefault();

    var datos = new FormData(form);
    if (e.submitter && e.submitter.name) datos.append(e.submitter.name, e.submitter.value);
    var pagina = urlDeLaPagina(zona);
    var nombre = zona.dataset.zona;
    zona.classList.add("actualizando");

    fetch(form.action, { method: "POST", body: datos, credentials: "same-origin", referrer: pagina })
      .then(function (r) {
        if (!r.ok) throw new Error("no se guardó");
        // Si nos devolvió justo esta página (con el mismo día o mes), la usamos; si no, la pedimos
        var vuelta = new URL(r.url), aqui = new URL(pagina, location.href);
        var misma = vuelta.pathname === aqui.pathname && vuelta.search === aqui.search;
        return misma ? r.text() : pedirPagina(pagina);
      })
      .then(function (html) {
        var nueva = new DOMParser().parseFromString(html, "text/html");
        var mensaje = nueva.querySelector(".aviso-exito p");
        mostrarAviso(mensaje && mensaje.textContent.replace(/^✓\s*/, ""));
        var modelo = buscarZona(nueva, nombre);
        // La zona tocada y sus copias en otras páginas del scroll continuo
        var copias = zonasLlamadas(document, nombre);
        if (copias.indexOf(zona) === -1) copias.push(zona);
        copias.forEach(function (vieja) {
          if (!modelo) { vieja.remove(); return; }   // ya no existe (borrada o ya no toca aquí)
          var reemplazo = document.importNode(modelo, true);
          // Lo que aparece con animación, aquí ya se ve
          reemplazo.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("visible"); });
          if (reemplazo.classList.contains("reveal")) reemplazo.classList.add("visible");
          vieja.replaceWith(reemplazo);
          if (window.Weblife) window.Weblife.preparar(reemplazo);
        });
      })
      .catch(function () {
        zona.classList.remove("actualizando");
        form.submit();   // si algo falla, como siempre
      });
  });
})();
