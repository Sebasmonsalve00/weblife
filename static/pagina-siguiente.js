// ============================================================
//  pagina-siguiente.js - Scroll continuo entre páginas
//
//  - Al final de la página, si sigues bajando (rueda, trackpad o dedo), se
//    llena el círculo de "Siguiente" y pasas a la página siguiente.
//  - Al principio de la página, si sigues subiendo, aparece "Anterior" y
//    vuelves a la página anterior (que se abre por el final).
//  Si paras o cambias de sentido, todo vuelve a su sitio.
//  El orden de páginas y los umbrales están en config_diseno.py.
// ============================================================

(function () {
  "use strict";
  var config = window.WEBLIFE || {};
  var ajustes = config.siguiente || {};
  var raiz = document.documentElement;
  var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Las dos direcciones: "abajo" (siguiente) y "arriba" (anterior).
  var bloqueSiguiente = document.getElementById("siguiente");
  var avisoAnterior = ajustes.anterior !== false ? document.getElementById("anterior") : null;
  if (!bloqueSiguiente && !avisoAnterior) return;
  // En el móvil, tirar hacia abajo arriba del todo recargaría la página: lo usamos para "Anterior".
  if (avisoAnterior && !sinMovimiento) raiz.style.overscrollBehaviorY = "none";

  // ---------- Precarga de la página siguiente cuando el footer entra en pantalla ----------
  // Añade <link rel="prefetch"> una sola vez por dirección.
  function precargar(enlace) {
    if (!enlace || enlace._precargada) return;
    enlace._precargada = true;
    var link = document.createElement("link");
    link.rel = "prefetch";
    link.href = enlace.getAttribute("href");
    document.head.appendChild(link);
  }
  var footer = document.querySelector(".footer");
  if (footer && bloqueSiguiente && "IntersectionObserver" in window) {
    new IntersectionObserver(function (entradas, obs) {
      if (entradas[0].isIntersecting) { precargar(bloqueSiguiente); obs.disconnect(); }
    }).observe(footer);
  }
  precargar(avisoAnterior);   // la anterior casi siempre ya está en caché, pero por si acaso

  // ---------- Navegar (una sola vez) ----------
  var navegando = false;
  // Abre la página vecina. "direccion" decide cómo entra la nueva (desde abajo o desde arriba).
  function ir(enlace, direccion) {
    if (navegando || !enlace) return;
    navegando = true;
    try { sessionStorage.setItem("weblife-siguiente", direccion); } catch (e) { /* sin almacenamiento: transición normal */ }
    window.location.href = enlace.getAttribute("href");
  }
  // El bloque "Siguiente" también es un enlace normal: le damos la misma transición.
  if (bloqueSiguiente) {
    bloqueSiguiente.addEventListener("click", function (e) {
      e.preventDefault();
      ir(bloqueSiguiente, "abajo");
    });
  }

  // Con "reducir movimiento" solo queda el enlace (sin gesto).
  if (sinMovimiento) return;

  var umbralEscritorio = ajustes.umbralEscritorio || 180;
  var umbralMovil = ajustes.umbralMovil || 90;
  var esperaInercia = ajustes.esperaInercia || 200;
  var reinicio = ajustes.reinicio || 600;

  var acumulado = 0;          // px acumulados en la dirección actual
  var sentido = null;         // "abajo", "arriba" o null
  var umbral = umbralEscritorio;
  var llegadaAbajo = 0;       // momento en que se llegó al final (para ignorar la inercia)
  var llegadaArriba = 0;      // momento en que se llegó al principio
  var temporizador = null;

  // ¿Está el scroll en el final exacto de la página? (margen de 2px)
  function enElFinal() { return window.innerHeight + window.scrollY >= raiz.scrollHeight - 2; }
  // ¿Está arriba del todo?
  function enElPrincipio() { return window.scrollY <= 2; }

  // Anota cuándo se llega a cada borde, para empezar a contar un poco después.
  function revisarBordes() {
    var ahora = Date.now();
    if (enElFinal()) { if (!llegadaAbajo) llegadaAbajo = ahora; } else { llegadaAbajo = 0; if (sentido === "abajo") cancelar(); }
    if (enElPrincipio()) { if (!llegadaArriba) llegadaArriba = ahora; } else { llegadaArriba = 0; if (sentido === "arriba") cancelar(); }
  }
  window.addEventListener("scroll", function () { requestAnimationFrame(revisarBordes); }, { passive: true });
  revisarBordes();
  // Al cargar arriba del todo no hay que esperar la inercia (no venimos de un scroll).
  llegadaArriba = llegadaArriba ? llegadaArriba - esperaInercia : 0;

  // ¿Hay algo que impide el gesto? (menú abierto, panel o formulario abierto, foco en un campo)
  function bloqueado(objetivo, dir) {
    if (navegando) return true;
    if (document.body.classList.contains("menu-abierto")) return true;
    if (document.querySelector("main details[open], dialog[open]")) return true;
    var activo = document.activeElement;
    if (activo && (activo.matches("input, textarea, select") || activo.isContentEditable)) return true;
    // No interferimos con secciones animadas, carruseles ni cajas con su propio scroll.
    for (var el = objetivo; el && el !== document.body && el.nodeType === 1; el = el.parentElement) {
      if (el.matches(".scroll-section, [data-carrusel]")) return true;
      var estilo = getComputedStyle(el);
      if (/(auto|scroll)/.test(estilo.overflowY) && el.scrollHeight > el.clientHeight + 1) {
        var leQuedaAbajo = el.scrollTop + el.clientHeight < el.scrollHeight - 1;
        var leQuedaArriba = el.scrollTop > 1;
        if ((dir === "abajo" && leQuedaAbajo) || (dir === "arriba" && leQuedaArriba)) return true;
      }
    }
    return false;
  }

  // Dibuja el avance en las variables CSS --siguiente y --anterior.
  function pintar() {
    var avance = Math.min(1, acumulado / umbral);
    raiz.style.setProperty("--siguiente", sentido === "abajo" ? avance.toFixed(3) : "0");
    raiz.style.setProperty("--anterior", sentido === "arriba" ? avance.toFixed(3) : "0");
  }

  // Vuelve todo a su sitio con una animación suave (la hace el CSS).
  function cancelar() {
    acumulado = 0;
    sentido = null;
    raiz.classList.remove("siguiente-activo");
    pintar();
  }

  // Suma desplazamiento en una dirección y decide si ya toca cambiar de página.
  function sumar(cantidad, dir, umbralUsado) {
    if (sentido !== dir) { acumulado = 0; sentido = dir; }
    umbral = umbralUsado;
    acumulado += cantidad;
    raiz.classList.add("siguiente-activo");   // sin transición mientras sigue el gesto
    pintar();
    clearTimeout(temporizador);
    temporizador = setTimeout(cancelar, reinicio);   // si deja de moverse, se cancela
    if (acumulado >= umbral) {
      if (dir === "abajo") ir(bloqueSiguiente, "abajo");
      else ir(avisoAnterior, "arriba");
    }
  }

  // ¿Se puede contar en esa dirección? (en el borde y pasada la espera de inercia)
  function listo(dir) {
    var ahora = Date.now();
    if (dir === "abajo") return bloqueSiguiente && enElFinal() && llegadaAbajo && ahora - llegadaAbajo >= esperaInercia;
    return avisoAnterior && enElPrincipio() && llegadaArriba && ahora - llegadaArriba >= esperaInercia;
  }

  // Recibe un movimiento (positivo = hacia abajo) y lo reparte.
  function mover(px, objetivo, umbralUsado) {
    var dir = px > 0 ? "abajo" : "arriba";
    if (sentido && sentido !== dir) { cancelar(); }   // cambió de sentido: se cancela
    if (!listo(dir) || bloqueado(objetivo, dir)) return;
    sumar(Math.abs(px), dir, umbralUsado);
  }

  // ---------- Escritorio: rueda o trackpad ----------
  window.addEventListener("wheel", function (e) {
    if (!e.deltaY) return;
    // deltaMode 1 = líneas, 2 = páginas: lo pasamos a píxeles
    var px = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? window.innerHeight : 1);
    mover(px, e.target, umbralEscritorio);
  }, { passive: true });

  // ---------- Móvil: arrastre del dedo ----------
  var ultimoY = null;
  window.addEventListener("touchstart", function (e) { ultimoY = e.touches[0].clientY; }, { passive: true });
  window.addEventListener("touchmove", function (e) {
    if (ultimoY === null) return;
    var y = e.touches[0].clientY;
    var arrastre = ultimoY - y;   // positivo = el dedo sube = la página quiere bajar
    ultimoY = y;
    if (arrastre) mover(arrastre, e.target, umbralMovil);
  }, { passive: true });
  window.addEventListener("touchend", function () { ultimoY = null; }, { passive: true });

  // Al volver con el botón "atrás", la página puede quedar a medio camino: la reiniciamos.
  window.addEventListener("pageshow", function () { navegando = false; cancelar(); });
})();
