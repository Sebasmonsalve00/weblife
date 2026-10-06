// ============================================================
//  pagina-siguiente.js - Pasar a la siguiente página al seguir bajando
//
//  Al llegar al final de la página, si sigues bajando (rueda, trackpad o
//  dedo), se va llenando el círculo del bloque "Siguiente". Al llegar al
//  umbral se abre la página siguiente. Si paras o subes, todo vuelve a su sitio.
//  El orden de páginas y los umbrales están en config_diseno.py.
// ============================================================

(function () {
  "use strict";
  var config = window.WEBLIFE || {};
  var ajustes = config.siguiente || {};
  var bloque = document.getElementById("siguiente");
  if (!bloque) return;   // última página o página fuera del orden

  var raiz = document.documentElement;
  var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var destino = bloque.getAttribute("href");

  // ---------- Precarga de la página siguiente cuando el footer entra en pantalla ----------
  var footer = document.querySelector(".footer");
  var precargada = false;
  // Añade <link rel="prefetch"> una sola vez.
  function precargar() {
    if (precargada) return;
    precargada = true;
    var link = document.createElement("link");
    link.rel = "prefetch";
    link.href = destino;
    document.head.appendChild(link);
  }
  if (footer && "IntersectionObserver" in window) {
    new IntersectionObserver(function (entradas, obs) {
      if (entradas[0].isIntersecting) { precargar(); obs.disconnect(); }
    }).observe(footer);
  }

  // ---------- Navegar (una sola vez) ----------
  var navegando = false;
  // Abre la página siguiente con la transición "hacia arriba".
  function ir() {
    if (navegando) return;
    navegando = true;
    try { sessionStorage.setItem("weblife-siguiente", "1"); } catch (e) { /* sin almacenamiento: transición normal */ }
    window.location.href = destino;
  }
  // El bloque también es un enlace normal: le damos la misma transición.
  bloque.addEventListener("click", function (e) {
    e.preventDefault();
    ir();
  });

  // Con "reducir movimiento" solo queda el enlace (sin gesto).
  if (sinMovimiento) return;

  var umbralEscritorio = ajustes.umbralEscritorio || 300;
  var umbralMovil = ajustes.umbralMovil || 120;
  var esperaInercia = ajustes.esperaInercia || 400;
  var reinicio = ajustes.reinicio || 600;

  var acumulado = 0;
  var umbral = umbralEscritorio;
  var llegadaAlFinal = 0;      // momento en que se llegó al final (para ignorar la inercia)
  var temporizador = null;

  // ¿Está el scroll en el final exacto de la página? (margen de 2px)
  function enElFinal() {
    return window.innerHeight + window.scrollY >= raiz.scrollHeight - 2;
  }

  // Vigilamos cuándo se llega al final para empezar a contar 400ms después.
  function revisarFinal() {
    if (enElFinal()) { if (!llegadaAlFinal) llegadaAlFinal = Date.now(); }
    else { llegadaAlFinal = 0; if (acumulado) cancelar(); }
  }
  window.addEventListener("scroll", function () { requestAnimationFrame(revisarFinal); }, { passive: true });
  revisarFinal();

  // ¿Hay algo que impide el gesto? (menú abierto, panel o formulario abierto, foco en un campo)
  function bloqueado(objetivo) {
    if (navegando) return true;
    if (document.body.classList.contains("menu-abierto")) return true;
    if (document.querySelector("main details[open], dialog[open]")) return true;
    var activo = document.activeElement;
    if (activo && (activo.matches("input, textarea, select") || activo.isContentEditable)) return true;
    // No interferimos con secciones animadas, carruseles ni cajas con su propio scroll.
    for (var el = objetivo; el && el !== document.body && el.nodeType === 1; el = el.parentElement) {
      if (el.matches(".scroll-section, [data-carrusel]")) return true;
      var estilo = getComputedStyle(el);
      var desplazable = /(auto|scroll)/.test(estilo.overflowY) && el.scrollHeight > el.clientHeight + 1;
      if (desplazable && el.scrollTop + el.clientHeight < el.scrollHeight - 1) return true;
    }
    return false;
  }

  // Dibuja el avance: el contenido sube y se aclara, el bloque crece y el círculo se llena.
  function pintar() {
    var avance = Math.min(1, acumulado / umbral);
    raiz.style.setProperty("--siguiente", avance.toFixed(3));
    bloque.setAttribute("data-avance", Math.round(avance * 100));
  }

  // Vuelve todo a su sitio con una animación suave (la hace el CSS en 400ms).
  function cancelar() {
    acumulado = 0;
    raiz.classList.remove("siguiente-activo");
    pintar();
  }

  // Suma desplazamiento y decide si ya toca cambiar de página.
  function sumar(cantidad, umbralUsado) {
    umbral = umbralUsado;
    acumulado += cantidad;
    raiz.classList.add("siguiente-activo");   // sin transición mientras sigue el gesto
    pintar();
    clearTimeout(temporizador);
    temporizador = setTimeout(cancelar, reinicio);   // si deja de bajar 600ms, se cancela
    if (acumulado >= umbral) ir();
  }

  // ¿Ya pasaron los 400ms desde que se llegó al final?
  function listoParaContar() {
    return enElFinal() && llegadaAlFinal && Date.now() - llegadaAlFinal >= esperaInercia;
  }

  // ---------- Escritorio: rueda o trackpad ----------
  window.addEventListener("wheel", function (e) {
    if (e.deltaY < 0) { if (acumulado) cancelar(); return; }   // sube: se cancela
    if (!listoParaContar() || bloqueado(e.target)) return;
    // deltaMode 1 = líneas, 2 = páginas: lo pasamos a píxeles
    var px = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? window.innerHeight : 1);
    sumar(px, umbralEscritorio);
  }, { passive: true });

  // ---------- Móvil: dedo arrastrado hacia arriba ----------
  var ultimoY = null;
  window.addEventListener("touchstart", function (e) {
    ultimoY = e.touches[0].clientY;
  }, { passive: true });
  window.addEventListener("touchmove", function (e) {
    if (ultimoY === null) return;
    var y = e.touches[0].clientY;
    var arrastre = ultimoY - y;   // positivo = el dedo sube = la página quiere bajar
    ultimoY = y;
    if (arrastre < 0) { if (acumulado) cancelar(); return; }
    if (!listoParaContar() || bloqueado(e.target)) return;
    sumar(arrastre, umbralMovil);
  }, { passive: true });
  window.addEventListener("touchend", function () { ultimoY = null; }, { passive: true });

  // Al volver con el botón "atrás", la página puede quedar a medio camino: la reiniciamos.
  window.addEventListener("pageshow", function () { navegando = false; cancelar(); });
})();
