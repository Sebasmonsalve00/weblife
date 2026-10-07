// ============================================================
//  selectores.js - Elegir fecha y hora con el estilo de la web
//
//  Los navegadores traen su propio calendario y su propia lista de horas,
//  cada uno con su aspecto. Aquí los cambiamos por unos nuestros: una
//  tarjeta de cristal con el mes (fechas) o con dos columnas de horas y
//  minutos (horas). El <input type="date"> o "time" de siempre sigue ahí,
//  escondido: es el que se envía con el formulario, así que nada más cambia.
//  Funciona también con lo que aparece después (scroll continuo, zonas).
// ============================================================

(function () {
  "use strict";
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var DIAS = ["L", "M", "X", "J", "V", "S", "D"];
  var DIAS_CORTOS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  var PASO_MINUTOS = 5;
  var conPopover = typeof HTMLElement !== "undefined" && "popover" in HTMLElement.prototype;

  function dos(n) { return (n < 10 ? "0" : "") + n; }
  function aTexto(fecha) { return fecha.getFullYear() + "-" + dos(fecha.getMonth() + 1) + "-" + dos(fecha.getDate()); }
  function deTexto(texto) {
    var p = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto || "");
    return p ? new Date(+p[1], +p[2] - 1, +p[3]) : null;
  }
  function crear(etiqueta, clase, texto) {
    var el = document.createElement(etiqueta);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;
    return el;
  }

  // Avisar al resto de la página de que el valor cambió (como si lo hubieras escrito)
  function avisar(input) {
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // ---------- La tarjeta flotante (una sola para toda la página) ----------
  var tarjeta = null, abiertoPara = null;
  function cerrar() {
    if (!tarjeta || !abiertoPara) return;
    if (conPopover) { try { tarjeta.hidePopover(); } catch (e) { /* ya cerrada */ } }
    tarjeta.hidden = true;
    abiertoPara.boton.setAttribute("aria-expanded", "false");
    abiertoPara = null;
  }
  function abrir(campo, pintar) {
    if (abiertoPara === campo) { cerrar(); return; }
    cerrar();
    if (!tarjeta) {
      tarjeta = crear("div", "selector-flotante vidrio");
      tarjeta.setAttribute("role", "dialog");
      if (conPopover) tarjeta.setAttribute("popover", "manual");
    }
    // Dentro de una ventana (dialog) la tarjeta va con ella; si no, en el body
    var dueno = campo.boton.closest("dialog") || document.body;
    if (tarjeta.parentNode !== dueno) dueno.appendChild(tarjeta);
    tarjeta.innerHTML = "";
    tarjeta.hidden = false;
    abiertoPara = campo;
    campo.boton.setAttribute("aria-expanded", "true");
    pintar(tarjeta);
    if (conPopover) { try { tarjeta.showPopover(); } catch (e) { /* sin popover */ } }
    colocar();
    var primero = tarjeta.querySelector(".elegido, .hoy, button");
    if (primero) primero.focus({ preventScroll: true });
  }
  // Debajo del campo; si no cabe, encima
  function colocar() {
    if (!abiertoPara) return;
    var caja = abiertoPara.boton.getBoundingClientRect();
    var alto = tarjeta.offsetHeight, ancho = tarjeta.offsetWidth;
    var arriba = caja.bottom + 8;
    if (arriba + alto > window.innerHeight - 8 && caja.top - alto - 8 > 8) arriba = caja.top - alto - 8;
    var izquierda = Math.min(Math.max(8, caja.left), window.innerWidth - ancho - 8);
    tarjeta.style.top = arriba + "px";
    tarjeta.style.left = izquierda + "px";
  }
  window.addEventListener("resize", colocar);
  window.addEventListener("scroll", colocar, { passive: true });
  document.addEventListener("pointerdown", function (e) {
    if (!abiertoPara) return;
    if (tarjeta.contains(e.target) || abiertoPara.envoltorio.contains(e.target)) return;
    cerrar();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && abiertoPara) {
      var boton = abiertoPara.boton;
      e.preventDefault(); e.stopPropagation();
      cerrar(); boton.focus();
    }
  }, true);

  // ---------- Fecha: un mes como el calendario de la web ----------
  function pintarMes(campo, tarjeta, mes) {
    var input = campo.input;
    var elegido = deTexto(input.value);
    var hoy = new Date(); hoy.setHours(0, 0, 0, 0);
    var minimo = deTexto(input.min), maximo = deTexto(input.max);
    tarjeta.innerHTML = "";
    tarjeta.className = "selector-flotante vidrio selector-mes";

    var cabecera = crear("div", "selector-cabecera");
    var anterior = crear("button", "boton-icono", "‹");
    var siguiente = crear("button", "boton-icono", "›");
    anterior.type = siguiente.type = "button";
    anterior.setAttribute("aria-label", "Mes anterior");
    siguiente.setAttribute("aria-label", "Mes siguiente");
    anterior.onclick = function () { pintarMes(campo, tarjeta, new Date(mes.getFullYear(), mes.getMonth() - 1, 1)); colocar(); };
    siguiente.onclick = function () { pintarMes(campo, tarjeta, new Date(mes.getFullYear(), mes.getMonth() + 1, 1)); colocar(); };
    var titulo = crear("b", "", MESES[mes.getMonth()].replace(/^./, function (l) { return l.toUpperCase(); }) + " " + mes.getFullYear());
    cabecera.append(titulo, anterior, siguiente);
    tarjeta.appendChild(cabecera);

    var rejilla = crear("div", "selector-dias");
    DIAS.forEach(function (d) { rejilla.appendChild(crear("span", "selector-dia-nombre", d)); });
    // Huecos antes del día 1 (la semana empieza el lunes)
    var hueco = (new Date(mes.getFullYear(), mes.getMonth(), 1).getDay() + 6) % 7;
    for (var i = 0; i < hueco; i++) rejilla.appendChild(crear("span"));
    var dias = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate();
    for (var dia = 1; dia <= dias; dia++) {
      var fecha = new Date(mes.getFullYear(), mes.getMonth(), dia);
      var boton = crear("button", "selector-dia", String(dia));
      boton.type = "button";
      boton.setAttribute("aria-label", dia + " de " + MESES[mes.getMonth()] + " de " + mes.getFullYear());
      if (+fecha === +hoy) boton.classList.add("hoy");
      if (elegido && +fecha === +elegido) { boton.classList.add("elegido"); boton.setAttribute("aria-pressed", "true"); }
      if ((minimo && fecha < minimo) || (maximo && fecha > maximo)) boton.disabled = true;
      boton.onclick = (function (f) { return function () { elegir(campo, aTexto(f)); }; })(fecha);
      rejilla.appendChild(boton);
    }
    tarjeta.appendChild(rejilla);

    var pie = crear("div", "selector-pie-fecha");
    if (!input.required) {
      var borrar = crear("button", "boton boton-secundario boton-chico", "Borrar");
      borrar.type = "button";
      borrar.onclick = function () { elegir(campo, ""); };
      pie.appendChild(borrar);
    }
    var botonHoy = crear("button", "boton boton-secundario boton-chico", "Hoy");
    botonHoy.type = "button";
    botonHoy.onclick = function () { elegir(campo, aTexto(hoy)); };
    pie.appendChild(botonHoy);
    tarjeta.appendChild(pie);
  }

  // ---------- Hora: dos columnas, horas y minutos ----------
  function pintarHoras(campo, tarjeta) {
    var input = campo.input;
    var actual = /^(\d{2}):(\d{2})/.exec(input.value) || null;
    var hora = actual ? +actual[1] : null, minuto = actual ? +actual[2] : null;
    var min = /^(\d{2}):(\d{2})/.exec(input.min || "") , max = /^(\d{2}):(\d{2})/.exec(input.max || "");
    var desde = min ? +min[1] : 0, hasta = max ? +max[1] : 23;
    tarjeta.innerHTML = "";
    tarjeta.className = "selector-flotante vidrio selector-horas";

    var columnas = crear("div", "selector-columnas");
    var colHoras = crear("div", "selector-columna"), colMinutos = crear("div", "selector-columna");
    colHoras.setAttribute("aria-label", "Hora"); colMinutos.setAttribute("aria-label", "Minutos");
    function pintar() {
      colHoras.innerHTML = ""; colMinutos.innerHTML = "";
      for (var h = desde; h <= hasta; h++) {
        var b = crear("button", "selector-opcion" + (h === hora ? " elegido" : ""), dos(h));
        b.type = "button";
        b.onclick = (function (valor) { return function () { hora = valor; if (minuto === null) minuto = 0; guardar(false); }; })(h);
        colHoras.appendChild(b);
      }
      var minutos = [];
      for (var m = 0; m < 60; m += PASO_MINUTOS) minutos.push(m);
      if (minuto !== null && minutos.indexOf(minuto) === -1) { minutos.push(minuto); minutos.sort(function (a, b) { return a - b; }); }
      minutos.forEach(function (m) {
        // Con hora máxima (ej: 20:00) no se puede pasar de esa hora
        var fuera = max && hora === hasta && m > +max[2];
        var b = crear("button", "selector-opcion" + (m === minuto ? " elegido" : ""), dos(m));
        b.type = "button"; b.disabled = !!fuera;
        b.onclick = function () { minuto = m; if (hora === null) hora = desde; guardar(true); };
        colMinutos.appendChild(b);
      });
    }
    function guardar(cerrarAlFinal) {
      if (max && hora === hasta && minuto > +max[2]) minuto = +max[2];
      var valor = dos(hora) + ":" + dos(minuto);
      if (input.value !== valor) { input.value = valor; avisar(input); }
      pintar();
      if (cerrarAlFinal) { cerrar(); campo.boton.focus(); }
    }
    pintar();
    columnas.append(colHoras, crear("span", "selector-dos-puntos", ":"), colMinutos);
    tarjeta.appendChild(columnas);

    var pie = crear("div", "selector-pie-fecha");
    if (!input.required) {
      var quitar = crear("button", "boton boton-secundario boton-chico", "Sin hora");
      quitar.type = "button";
      quitar.onclick = function () { if (input.value) { input.value = ""; avisar(input); } cerrar(); campo.boton.focus(); };
      pie.appendChild(quitar);
    }
    var listo = crear("button", "boton boton-primario boton-chico", "Listo");
    listo.type = "button";
    listo.onclick = function () {
      if (!input.value && hora === null) { hora = desde; minuto = 0; }
      if (hora !== null) guardar(false);
      cerrar(); campo.boton.focus();
    };
    pie.appendChild(listo);
    tarjeta.appendChild(pie);

    // Que se vea la hora elegida sin tener que buscarla
    requestAnimationFrame(function () {
      [colHoras, colMinutos].forEach(function (col) {
        var el = col.querySelector(".elegido");
        if (el) col.scrollTop = el.offsetTop - col.clientHeight / 2 + el.offsetHeight / 2;
      });
    });
  }

  function elegir(campo, valor) {
    if (campo.input.value !== valor) { campo.input.value = valor; avisar(campo.input); }
    cerrar();
    campo.boton.focus();
  }

  // ---------- Convertir cada campo ----------
  function textoDe(input) {
    if (input.type === "date") {
      var f = deTexto(input.value);
      return f ? DIAS_CORTOS[f.getDay()] + ", " + f.getDate() + " " + MESES[f.getMonth()].slice(0, 3) + " " + f.getFullYear() : "";
    }
    return /^\d{2}:\d{2}/.test(input.value) ? input.value.slice(0, 5) : "";
  }

  function preparar(input) {
    if (input.dataset.selector) return;
    input.dataset.selector = "1";
    var esFecha = input.type === "date";
    var envoltorio = crear("span", "selector-campo");
    var boton = crear("button", "selector-boton");
    boton.type = "button";
    boton.setAttribute("aria-haspopup", "dialog");
    boton.setAttribute("aria-expanded", "false");
    var texto = crear("span", "selector-texto");
    var icono = crear("span", "selector-icono");
    icono.setAttribute("aria-hidden", "true");
    icono.innerHTML = esFecha
      ? '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15" rx="3.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>'
      : '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>';
    boton.append(texto, icono);
    input.parentNode.insertBefore(envoltorio, input);
    envoltorio.append(input, boton);
    input.classList.add("selector-original");
    input.tabIndex = -1;
    var campo = { input: input, boton: boton, envoltorio: envoltorio };

    function pintarBoton() {
      var t = textoDe(input);
      texto.textContent = t || (esFecha ? "Elegir fecha" : "Sin hora");
      boton.classList.toggle("vacio", !t);
      var etiqueta = input.id && document.querySelector("label[for='" + input.id + "']");
      boton.setAttribute("aria-label", (etiqueta ? etiqueta.textContent.trim() + ": " : "") + (t || texto.textContent));
    }
    // Si un script cambia el valor (por ejemplo, al abrir "Editar"), el botón se actualiza solo
    var propio = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    Object.defineProperty(input, "value", {
      configurable: true,
      get: function () { return propio.get.call(this); },
      set: function (v) { propio.set.call(this, v); pintarBoton(); }
    });
    input.addEventListener("change", pintarBoton);
    if (input.form) input.form.addEventListener("reset", function () { setTimeout(pintarBoton); });
    // La etiqueta del campo abre el selector
    input.addEventListener("focus", function () { boton.focus(); });
    if (input.id) {
      document.addEventListener("click", function (e) {
        var l = e.target.closest && e.target.closest("label[for='" + input.id + "']");
        if (l) { e.preventDefault(); boton.click(); }
      });
    }
    boton.addEventListener("click", function () {
      abrir(campo, function (t) {
        if (esFecha) pintarMes(campo, t, (function (f) { return new Date(f.getFullYear(), f.getMonth(), 1); })(deTexto(input.value) || new Date()));
        else pintarHoras(campo, t);
      });
    });
    // Si el formulario se envía sin rellenar un campo obligatorio, se marca el botón
    input.addEventListener("invalid", function () { boton.classList.add("invalido"); boton.focus(); });
    input.addEventListener("change", function () { boton.classList.remove("invalido"); });
    pintarBoton();
  }

  function prepararTodo(raiz) {
    if (raiz.matches && raiz.matches("input[type=date], input[type=time]")) preparar(raiz);
    raiz.querySelectorAll("input[type=date], input[type=time]").forEach(preparar);
  }
  prepararTodo(document);
  // Lo que se añade después (la página siguiente, una zona actualizada...)
  new MutationObserver(function (cambios) {
    cambios.forEach(function (c) {
      c.addedNodes.forEach(function (n) { if (n.nodeType === 1) prepararTodo(n); });
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
