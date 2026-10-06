// ============================================================
//  scroll-engine.js - Motor de animaciones ligadas al scroll
//
//  1. Secciones con scroll animado:
//     <section class="scroll-section" style="--alto: var(--alto-media)">
//       <div class="scroll-sticky">
//         <h2 data-anim="opacity" data-start="0.1" data-end="0.3" data-from="0" data-to="1">...</h2>
//       </div>
//     </section>
//     El motor calcula el progreso de la sección (de 0 a 1), lo guarda en la
//     variable CSS --progress y mueve los elementos con data-anim.
//     Tipos: opacity, translateY, translateX, scale, blur.
//     Varios efectos en un mismo elemento: separa con "|" en cada atributo,
//     por ejemplo data-anim="opacity|translateY" data-from="0|60" data-to="1|0".
//
//  2. Titulares por palabra: <h2 data-revelar-palabras>Texto</h2>
//     Cada palabra pasa del 15% al 100% de opacidad mientras el titular sube
//     desde el borde inferior de la pantalla hasta la mitad.
//
//  Se actualiza con requestAnimationFrame (nunca dentro del evento scroll) y
//  solo para lo que está en pantalla (IntersectionObserver).
//  Solo anima transform, opacity y filter.
// ============================================================

(function () {
  "use strict";
  var config = window.WEBLIFE || {};
  var efectos = config.efectos || {};
  var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Curva cubic-bezier(0.16, 1, 0.3, 1) ----------
  // Devuelve una función que convierte un avance lineal (0 a 1) en uno suavizado.
  function curvaBezier(x1, y1, x2, y2) {
    function coord(t, a, b) {   // punto de la curva en el eje a/b para el instante t
      return 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t;
    }
    return function (x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      // Buscamos el t cuya x es la pedida (búsqueda binaria, suficiente para animar)
      var bajo = 0, alto = 1, t = x;
      for (var i = 0; i < 20; i++) {
        t = (bajo + alto) / 2;
        if (coord(t, x1, x2) < x) bajo = t; else alto = t;
      }
      return coord(t, y1, y2);
    };
  }
  var suavizar = curvaBezier(0.16, 1, 0.3, 1);

  // Limita un número entre 0 y 1.
  function limitar(n) { return Math.max(0, Math.min(1, n)); }

  // Avance dentro de un rango: 0 antes de "inicio", 1 después de "fin", suavizado en medio.
  function avanceEnRango(progreso, inicio, fin) {
    if (fin <= inicio) return progreso >= fin ? 1 : 0;
    return suavizar(limitar((progreso - inicio) / (fin - inicio)));
  }

  // ---------- 1. Secciones con scroll animado ----------

  // Lee los atributos data-anim de un elemento y prepara su lista de efectos.
  function leerEfectos(el) {
    var partes = function (nombre, porDefecto) {
      return (el.getAttribute(nombre) || porDefecto).split("|");
    };
    var tipos = partes("data-anim", "");
    var inicios = partes("data-start", "0"), fines = partes("data-end", "1");
    var desde = partes("data-from", "0"), hasta = partes("data-to", "1");
    return tipos.map(function (tipo, i) {
      var elegir = function (lista) { return parseFloat(lista[i] !== undefined ? lista[i] : lista[0]); };
      return { tipo: tipo.trim(), inicio: elegir(inicios), fin: elegir(fines), desde: elegir(desde), hasta: elegir(hasta) };
    });
  }

  // Aplica a un elemento todos sus efectos para el progreso dado.
  function pintarElemento(item, progreso) {
    var transformaciones = [], opacidad = null, desenfoque = null;
    item.efectos.forEach(function (e) {
      var valor = e.desde + (e.hasta - e.desde) * avanceEnRango(progreso, e.inicio, e.fin);
      if (e.tipo === "opacity") opacidad = valor;
      else if (e.tipo === "translateY") transformaciones.push("translateY(" + valor + "px)");
      else if (e.tipo === "translateX") transformaciones.push("translateX(" + valor + "px)");
      else if (e.tipo === "scale") transformaciones.push("scale(" + valor + ")");
      else if (e.tipo === "blur") desenfoque = "blur(" + valor + "px)";
    });
    item.el.style.transform = transformaciones.join(" ");
    if (opacidad !== null) item.el.style.opacity = opacidad;
    if (desenfoque !== null) item.el.style.filter = desenfoque;
  }

  // Progreso de una sección: (scroll − inicio) / (alto − alto de ventana), entre 0 y 1.
  function progresoSeccion(seccion) {
    var caja = seccion.getBoundingClientRect();
    var recorrido = caja.height - window.innerHeight;
    if (recorrido <= 0) return caja.top <= 0 ? 1 : 0;
    return limitar(-caja.top / recorrido);
  }

  // ---------- 2. Titulares por palabra ----------

  // Parte el texto de un titular en <span> por palabra. Los lectores de pantalla leen el texto entero.
  function partirEnPalabras(titular) {
    var texto = titular.textContent.trim();
    if (!texto) return [];
    titular.setAttribute("aria-label", texto);
    titular.textContent = "";
    var palabras = texto.split(/\s+/);
    return palabras.map(function (palabra, i) {
      var span = document.createElement("span");
      span.className = "palabra";
      span.setAttribute("aria-hidden", "true");
      span.textContent = palabra;
      titular.appendChild(span);
      if (i < palabras.length - 1) titular.appendChild(document.createTextNode(" "));
      return span;
    });
  }

  // Progreso de un titular: 0 cuando asoma por abajo, 1 cuando llega a la mitad de la pantalla.
  function progresoTitular(titular) {
    var arriba = titular.getBoundingClientRect().top;
    var alto = window.innerHeight;
    return limitar((alto - arriba) / (alto * 0.5));
  }

  // ---------- Bucle de actualización ----------
  var activos = new Set();      // secciones y titulares que están en pantalla
  var pendiente = false;

  // Pide un dibujo en el próximo cuadro (como mucho uno por cuadro).
  function pedirDibujo() {
    if (pendiente) return;
    pendiente = true;
    requestAnimationFrame(dibujar);
  }

  // Dibuja todo lo que está activo.
  function dibujar() {
    pendiente = false;
    activos.forEach(function (cosa) { cosa.actualizar(); });
  }

  // Activa o desactiva cada cosa según si está en pantalla.
  var vigilante = ("IntersectionObserver" in window) ? new IntersectionObserver(function (entradas) {
    entradas.forEach(function (entrada) {
      var cosa = entrada.target._motor;
      if (!cosa) return;
      if (entrada.isIntersecting) { activos.add(cosa); cosa.alEntrar(); }
      else { cosa.actualizar(); activos.delete(cosa); cosa.alSalir(); }
    });
    pedirDibujo();
  }, { rootMargin: "100px 0px" }) : null;

  // Prepara una sección .scroll-section.
  function prepararSeccion(seccion) {
    var items = Array.prototype.map.call(seccion.querySelectorAll("[data-anim]"), function (el) {
      return { el: el, efectos: leerEfectos(el) };
    });
    var cosa = {
      actualizar: function () {
        var progreso = progresoSeccion(seccion);
        seccion.style.setProperty("--progress", progreso.toFixed(4));
        items.forEach(function (item) { pintarElemento(item, progreso); });
        seccion.dispatchEvent(new CustomEvent("progreso", { detail: progreso }));
      },
      // will-change solo mientras la sección está en pantalla
      alEntrar: function () { items.forEach(function (i) { i.el.style.willChange = "transform, opacity, filter"; }); },
      alSalir: function () { items.forEach(function (i) { i.el.style.willChange = ""; }); }
    };
    seccion._motor = cosa;
    vigilante.observe(seccion);
  }

  // Prepara un titular data-revelar-palabras.
  function prepararTitular(titular) {
    var palabras = partirEnPalabras(titular);
    if (!palabras.length) return;
    var inicial = config.palabraInicial !== undefined ? config.palabraInicial : 0.15;
    var cosa = {
      actualizar: function () {
        var progreso = progresoTitular(titular);
        // Cada palabra tiene su tramo: la 1ª empieza en 0, la última termina en 1.
        var n = palabras.length;
        palabras.forEach(function (span, i) {
          var inicio = i / (n + 1), fin = (i + 2) / (n + 1);
          span.style.opacity = inicial + (1 - inicial) * avanceEnRango(progreso, inicio, fin);
        });
      },
      alEntrar: function () {},
      alSalir: function () {}
    };
    titular._motor = cosa;
    titular.classList.add("palabras-listas");
    vigilante.observe(titular);
    cosa.actualizar();   // primer dibujo sin esperar, así no parpadea
  }

  // ---------- Arranque ----------
  // Con "reducir movimiento" o sin IntersectionObserver no se anima nada:
  // las secciones quedan a su altura natural (lo hace el CSS) y todo el texto se ve.
  if (sinMovimiento || !vigilante) return;
  if (efectos.motor_scroll !== false) {
    document.querySelectorAll(".scroll-section").forEach(prepararSeccion);
  }
  if (efectos.titulares_por_palabra !== false) {
    document.querySelectorAll("[data-revelar-palabras]").forEach(prepararTitular);
  }
  window.addEventListener("scroll", pedirDibujo, { passive: true });
  window.addEventListener("resize", pedirDibujo);

  // Lo dejamos disponible para otros archivos (por ejemplo una futura portada con secuencia).
  window.ScrollEngine = { pedirDibujo: pedirDibujo, suavizar: suavizar, avanceEnRango: avanceEnRango };
})();
