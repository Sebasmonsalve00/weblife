// ============================================================
//  app.js - Pequeños comportamientos de la web
//  1. Menú que se achica al bajar
//  2. Menú móvil (abrir/cerrar con X, Escape o al hacer clic)
//  3. Animaciones al hacer scroll (.reveal)
//  4. Validación en vivo de los formularios
//  5. Interruptor Universidad / Deporte del header
//  Los tiempos vienen de config_diseno.py (window.WEBLIFE).
// ============================================================

(function () {
  "use strict";
  var config = window.WEBLIFE || { escalonado: 100, menuRetraso: 60, mensajes: {} };
  var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Marcamos que hay JavaScript: así los .reveal solo se ocultan si luego se pueden mostrar.
  document.documentElement.classList.add("js");

  // ---------- 1. Menú compacto al bajar más de 50px ----------
  var nav = document.getElementById("nav");
  if (nav) {
    var revisarScroll = function () {
      nav.classList.toggle("compacta", window.scrollY > 50);
    };
    window.addEventListener("scroll", revisarScroll, { passive: true });
    revisarScroll();
  }

  // ---------- 2. Menú móvil ----------
  var boton = document.getElementById("hamburguesa");
  var panel = document.getElementById("menu-movil");
  if (boton && panel) {
    var abrir = function () {
      panel.hidden = false;
      // Esperamos un cuadro para que la transición de entrada se vea
      requestAnimationFrame(function () { panel.classList.add("abierto"); });
      boton.setAttribute("aria-expanded", "true");
      boton.setAttribute("aria-label", "Cerrar menú");
      document.body.classList.add("menu-abierto");   // bloquea el scroll de la página
      var primero = panel.querySelector("a, button");
      if (primero) primero.focus();
    };
    var cerrar = function () {
      panel.classList.remove("abierto");
      boton.setAttribute("aria-expanded", "false");
      boton.setAttribute("aria-label", "Abrir menú");
      document.body.classList.remove("menu-abierto");
      setTimeout(function () { panel.hidden = true; }, sinMovimiento ? 0 : 300);
    };
    boton.addEventListener("click", function () {
      boton.getAttribute("aria-expanded") === "true" ? cerrar() : abrir();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && boton.getAttribute("aria-expanded") === "true") {
        cerrar();
        boton.focus();
      }
    });
    panel.querySelectorAll("a").forEach(function (enlace) {
      enlace.addEventListener("click", cerrar);
    });
    // Si la pantalla se agranda a escritorio, cerramos el panel
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 1024 && !panel.hidden) cerrar();
    });
  }

  // ---------- 3. Aparecer al hacer scroll ----------
  var observador = (sinMovimiento || !("IntersectionObserver" in window)) ? null :
    new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          entrada.target.classList.add("visible");
          observador.unobserve(entrada.target);   // se anima una sola vez
        }
      });
    }, { threshold: 0.15 });
  // Prepara los .reveal que hay dentro de "raiz"
  var prepararReveal = function (raiz) {
    var elementos = raiz.querySelectorAll(".reveal");
    // Retraso escalonado de 100ms entre hermanos (elementos .reveal con el mismo padre)
    elementos.forEach(function (el) {
      var padre = el.parentElement;
      if (padre) {
        var hermanos = Array.prototype.filter.call(padre.children, function (h) {
          return h.classList.contains("reveal");
        });
        el.style.transitionDelay = hermanos.indexOf(el) * config.escalonado + "ms";
      }
      if (observador) observador.observe(el); else el.classList.add("visible");
    });
  };

  // ---------- 4. Validación en vivo ----------
  var validar = function (input) {
    var campo = input.closest(".campo");
    if (!campo) return true;
    var mensaje = campo.querySelector(".mensaje-campo");
    if (!mensaje) {
      mensaje = document.createElement("small");
      mensaje.className = "mensaje-campo";
      mensaje.setAttribute("aria-live", "polite");
      campo.appendChild(mensaje);
    }
    var texto = "";
    if (input.validity.valueMissing) texto = config.mensajes.obligatorio;
    else if (input.validity.rangeUnderflow || input.validity.badInput) texto = config.mensajes.numero;
    else if (!input.validity.valid) texto = input.validationMessage;
    mensaje.textContent = texto;
    campo.classList.toggle("invalido", texto !== "");
    return texto === "";
  };
  // Prepara los formularios que hay dentro de "raiz"
  var prepararFormularios = function (raiz) {
    raiz.querySelectorAll("form").forEach(function (form) {
      var campos = form.querySelectorAll(".campo input, .campo select");
      if (!campos.length) return;
      // Usamos nuestros mensajes en vez de los globos del navegador
      form.noValidate = true;
      form.addEventListener("submit", function (e) {
        var primeroMalo = null;
        campos.forEach(function (input) {
          if (!validar(input) && !primeroMalo) primeroMalo = input;
        });
        if (primeroMalo) {
          e.preventDefault();
          primeroMalo.focus();
        }
      });
      campos.forEach(function (input) {
        input.addEventListener("blur", function () { validar(input); });
        input.addEventListener("input", function () {
          if (input.closest(".campo").classList.contains("invalido")) validar(input);
        });
      });
    });
  };

  // Preparamos la página, y dejamos la función a mano para el contenido que
  // se añade luego (el scroll continuo añade la página siguiente debajo).
  var preparar = function (raiz) {
    prepararReveal(raiz);
    prepararFormularios(raiz);
  };
  preparar(document);

  // ---------- 5. Interruptor Universidad / Deporte ----------
  // La bolita se desliza primero y luego se envía el cambio. Volvemos a la página
  // que estás viendo (con el scroll continuo la dirección puede haber cambiado).
  var formModo = document.getElementById("form-modo");
  if (formModo) {
    formModo.addEventListener("submit", function (e) {
      e.preventDefault();
      formModo.volver.value = location.pathname;
      var interruptor = formModo.querySelector(".interruptor-modo");
      interruptor.setAttribute("aria-checked", interruptor.getAttribute("aria-checked") === "true" ? "false" : "true");
      interruptor.disabled = true;
      setTimeout(function () { formModo.submit(); }, sinMovimiento ? 0 : 220);
    });
  }

  window.Weblife = { preparar: preparar };
})();
