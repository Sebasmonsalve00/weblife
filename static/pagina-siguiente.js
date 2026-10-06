// ============================================================
//  pagina-siguiente.js - Scroll continuo entre páginas
//
//  Cada página es un "tramo" (<div class="tramo">). Antes de que llegues al
//  final, se descarga la página siguiente y su tramo se añade debajo, así que
//  sigues bajando sin pararte y sin pantalla de carga. Al subir arriba del
//  todo pasa lo mismo con la página anterior, que aparece encima.
//  Mientras bajas, la dirección de la barra, el título de la pestaña y el
//  menú cambian a la página que estás viendo.
//  El orden de páginas y la precarga están en config_diseno.py.
// ============================================================

(function () {
  "use strict";
  var ajustes = (window.WEBLIFE || {}).siguiente || {};
  var precarga = ajustes.precarga || 1.5;   // pantallas de antelación
  var primero = document.querySelector(".tramo");
  if (!primero || !window.fetch || !window.DOMParser) return;
  var footer = document.querySelector(".footer");
  var cargadas = {};   // dirección -> true (cada página aparece una sola vez)
  cargadas[primero.dataset.url] = true;
  var cargando = { abajo: false, arriba: false };

  // ---------- Traer una página y sacar su tramo ----------
  var guardadas = {};   // dirección -> promesa con el documento (una descarga por página)
  function traer(url) {
    if (!guardadas[url]) {
      guardadas[url] = fetch(url, { credentials: "same-origin" }).then(function (r) {
        // Si la sesión caducó nos manda a "Entrar": entonces no seguimos
        if (!r.ok || r.redirected) throw new Error("sin página");
        return r.text();
      }).then(function (html) {
        return new DOMParser().parseFromString(html, "text/html");
      });
      guardadas[url].catch(function () { delete guardadas[url]; });
    }
    return guardadas[url];
  }

  // Convierte el tramo de otra página en uno de esta: su <main> pasa a ser un
  // <div> (solo puede haber un <main>) y sus scripts se vuelven a crear para que se ejecuten.
  function adoptar(doc) {
    var tramo = doc.querySelector(".tramo");
    if (!tramo) return null;
    tramo = document.importNode(tramo, true);
    tramo.classList.remove("actual");
    tramo.dataset.titulo = tramo.dataset.titulo || doc.title;
    var main = tramo.querySelector("main");
    if (main) {
      var div = document.createElement("div");
      div.className = main.className;
      while (main.firstChild) div.appendChild(main.firstChild);
      main.replaceWith(div);
    }
    // Los mensajes de "guardado" ya se vieron en su página
    tramo.querySelectorAll(".aviso-exito").forEach(function (el) { el.remove(); });
    return tramo;
  }

  // Ejecuta los scripts del tramo (al añadir HTML así, el navegador no los ejecuta solo)
  function activar(tramo) {
    tramo.querySelectorAll("script").forEach(function (viejo) {
      if (viejo.type && viejo.type !== "text/javascript") return;   // datos (JSON), no código
      var nuevo = document.createElement("script");
      nuevo.textContent = viejo.textContent;
      viejo.replaceWith(nuevo);
    });
    if (window.Weblife) window.Weblife.preparar(tramo);
    if (window.ScrollEngine && window.ScrollEngine.preparar) {
      window.ScrollEngine.preparar(tramo);
      window.ScrollEngine.pedirDibujo();
    }
  }

  // ---------- Hacia abajo: añadir la página siguiente debajo ----------
  function cargarSiguiente() {
    var tramos = document.querySelectorAll(".tramo");
    var ultimo = tramos[tramos.length - 1];
    var enlace = ultimo.querySelector(".siguiente");
    if (cargando.abajo || !enlace) return;
    var url = new URL(enlace.href).pathname;
    if (cargadas[url]) return;
    cargando.abajo = true;
    traer(url).then(function (doc) {
      var tramo = adoptar(doc);
      if (!tramo) throw new Error("sin tramo");
      cargadas[url] = true;
      ultimo.after(tramo);
      activar(tramo);
      vigilar(tramo);
      ajustarPegado();
    }).catch(function () {
      enlace.dataset.fallo = "1";   // si falla, el enlace sigue funcionando como siempre
    }).then(function () { cargando.abajo = false; revisar(); });
  }

  // ---------- Hacia arriba: añadir la página anterior encima ----------
  // La ponemos sin que lo que ves se mueva (corregimos el scroll con lo que mide).
  function cargarAnterior() {
    if (ajustes.anterior === false || cargando.arriba) return;
    var arriba = document.querySelector(".tramo");
    var url = arriba.dataset.anterior;
    if (!url || cargadas[url]) return;
    cargando.arriba = true;
    traer(url).then(function (doc) {
      var tramo = adoptar(doc);
      if (!tramo) throw new Error("sin tramo");
      cargadas[url] = true;
      var antes = arriba.getBoundingClientRect().top;
      arriba.before(tramo);
      activar(tramo);
      vigilar(tramo);
      ajustarPegado();
      window.scrollBy(0, arriba.getBoundingClientRect().top - antes);
    }).catch(function () {}).then(function () { cargando.arriba = false; });
  }

  // ---------- Página actual: barra de direcciones, título y menú ----------
  var actual = primero;
  function marcarActual(tramo) {
    if (tramo === actual) return;
    actual.classList.remove("actual");
    tramo.classList.add("actual");
    actual = tramo;
    var url = tramo.dataset.url;
    try { history.replaceState(history.state, "", url); } catch (e) { /* sin historial: da igual */ }
    if (tramo.dataset.titulo) document.title = tramo.dataset.titulo;
    // Los avisos del calendario solo se ven mientras estás en el calendario
    document.body.classList.toggle("con-avisos", tramo.classList.contains("con-avisos"));
    document.querySelectorAll(".nav-enlaces a, .menu-movil nav > a").forEach(function (a) {
      var es = new URL(a.href).pathname === url;
      a.classList.toggle("activo", es);
      if (es) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
  }

  // ---------- Revisar en cada cuadro de scroll ----------
  var ultimoY = window.scrollY;
  var pendiente = false;
  function revisar() {
    pendiente = false;
    var alto = window.innerHeight;
    var y = window.scrollY;
    // Cerca del final: traemos la siguiente para que ya esté cuando llegues
    var finalContenido = footer ? footer.getBoundingClientRect().top : document.documentElement.scrollHeight - y;
    if (finalContenido < alto * (1 + precarga)) cargarSiguiente();
    // Subiendo cerca del principio: traemos la anterior
    if (y < ultimoY && y < alto) cargarAnterior();
    ultimoY = y;
    // La página actual es la que ocupa la línea a 40% de la pantalla
    var linea = alto * 0.4;
    document.querySelectorAll(".tramo").forEach(function (t) {
      var caja = t.getBoundingClientRect();
      if (caja.top <= linea && caja.bottom > linea) marcarActual(t);
    });
    taparAnteriores(alto);
    difuminarAvisos(alto);
  }

  // ---------- Transición: la página se queda quieta y la siguiente sube por encima ----------
  // Cada página (menos la última) es "sticky": al llegar a su final se queda fija abajo,
  // y la siguiente sube tapándola. Mientras sube, lo de debajo se difumina y desaparece.
  function siguienteTramo(t) {
    var otro = t.nextElementSibling;
    return otro && otro.classList.contains("tramo") ? otro : null;
  }
  function ajustarPegado() {
    var alto = window.innerHeight;
    document.querySelectorAll(".tramo").forEach(function (t) {
      var pega = !!siguienteTramo(t);
      t.classList.toggle("pegado", pega);
      // Se queda fija cuando su borde de abajo toca el de la pantalla
      t.style.top = pega ? Math.min(0, alto - t.offsetHeight) + "px" : "";
    });
  }
  // --cubierto: 0 = la siguiente aún no asoma, 1 = la siguiente ya llena la pantalla
  function taparAnteriores(alto) {
    document.querySelectorAll(".tramo").forEach(function (t) {
      var debajo = siguienteTramo(t);
      var cubierto = debajo ? limitar(1 - debajo.getBoundingClientRect().top / alto) : 0;
      t.style.setProperty("--cubierto", cubierto.toFixed(3));
      t.classList.toggle("cubriendo", cubierto > 0);
      t.classList.toggle("tapado", cubierto >= 1);
    });
  }
  // Si una página cambia de alto (se abre un panel, carga algo), recalculamos
  var vigilaAlto = "ResizeObserver" in window ? new ResizeObserver(function () { ajustarPegado(); pedir(); }) : null;
  function vigilar(t) { if (vigilaAlto) vigilaAlto.observe(t); }
  document.querySelectorAll(".tramo").forEach(vigilar);
  window.addEventListener("resize", ajustarPegado);

  // Los avisos fijos del calendario se desvanecen (y se desenfocan) siguiendo el scroll:
  // empiezan a irse cuando la página siguiente asoma por el 70% de la pantalla y
  // desaparecen del todo cuando llega al 37%. Al subir, vuelven igual.
  var EMPIEZA = 0.70, TERMINA = 0.37;
  function limitar(n) { return Math.max(0, Math.min(1, n)); }
  function difuminarAvisos(alto) {
    document.querySelectorAll(".tramo .avisos").forEach(function (avisos) {
      var suyo = avisos.closest(".tramo");
      var caja = suyo.getBoundingClientRect();
      // Su página se queda quieta al final: lo que cuenta es dónde va la siguiente
      var debajo = siguienteTramo(suyo);
      var abajo = debajo ? debajo.getBoundingClientRect().top : caja.bottom;
      var tramo = EMPIEZA - TERMINA;
      var entra = limitar((EMPIEZA - caja.top / alto) / tramo);      // al llegar desde arriba
      var sale = limitar((abajo / alto - TERMINA) / tramo);          // al irse hacia abajo
      var visible = Math.min(entra, sale);
      avisos.style.setProperty("--avisos-visible", visible.toFixed(3));
      avisos.classList.toggle("avisos-fuera", visible === 0);   // del todo ido: no se puede pulsar
    });
  }
  function pedir() { if (!pendiente) { pendiente = true; requestAnimationFrame(revisar); } }
  window.addEventListener("scroll", pedir, { passive: true });
  window.addEventListener("resize", pedir);

  // Arriba del todo no hay evento de scroll: miramos la rueda y el dedo
  window.addEventListener("wheel", function (e) {
    if (e.deltaY < 0 && window.scrollY < window.innerHeight) cargarAnterior();
  }, { passive: true });
  var dedoY = null;
  window.addEventListener("touchstart", function (e) { dedoY = e.touches[0].clientY; }, { passive: true });
  window.addEventListener("touchmove", function (e) {
    if (dedoY !== null && e.touches[0].clientY > dedoY && window.scrollY < window.innerHeight) cargarAnterior();
  }, { passive: true });

  // El enlace "Siguiente" baja hasta la página siguiente si ya está debajo
  document.addEventListener("click", function (e) {
    var enlace = e.target.closest && e.target.closest(".siguiente");
    if (!enlace || enlace.dataset.fallo) return;
    var tramo = enlace.closest(".tramo");
    var siguiente = tramo && tramo.nextElementSibling;
    if (siguiente && siguiente.classList.contains("tramo")) {
      e.preventDefault();
      var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      siguiente.scrollIntoView({ behavior: sinMovimiento ? "auto" : "smooth" });
    }
  });

  // La anterior la dejamos descargada de antemano, para que aparezca al instante
  if (ajustes.anterior !== false && primero.dataset.anterior) {
    (window.requestIdleCallback || setTimeout)(function () { traer(primero.dataset.anterior); });
  }
  ajustarPegado();
  revisar();
})();
