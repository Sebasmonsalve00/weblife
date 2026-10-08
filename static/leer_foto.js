// ============================================================
//  leer_foto.js - "Sube tu horario" con una foto o captura
//
//  La foto se lee en tu propio navegador con Tesseract (un lector de texto
//  gratis): no se manda a ningún sitio. Se busca:
//    - los días de arriba ("lun 5/10", "Martes"...) para saber cada columna,
//    - en cada bloque, su hora ("9:00 - 12:00"), el nombre y el aula.
//  Luego enseña la lista para que marques las que están bien y las manda
//  al servidor como una tabla CSV, igual que si subieras un Excel.
//  Funciona mejor con capturas tipo pintahorarios, donde cada clase dice su hora.
// ============================================================

(function () {
  "use strict";
  var TESSERACT = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
  var OPCIONES = {
    workerPath: "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/worker.min.js",
    corePath: "https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1",
    langPath: "https://cdn.jsdelivr.net/npm/@tesseract.js-data/spa@1.0.0/4.0.0_best_int",
  };
  var DIAS = [["lun", "lunes", "mon"], ["mar", "martes", "tue"], ["mie", "mié", "miercoles", "miércoles", "wed"],
              ["jue", "jueves", "thu"], ["vie", "viernes", "fri"], ["sab", "sáb", "sabado", "sábado", "sat"],
              ["dom", "domingo", "sun"]];
  var NOMBRES_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

  function cargarTesseract() {
    if (window.Tesseract) return Promise.resolve(window.Tesseract);
    return new Promise(function (ok, mal) {
      var s = document.createElement("script");
      s.src = TESSERACT;
      s.onload = function () { ok(window.Tesseract); };
      s.onerror = function () { mal(new Error("No se pudo cargar el lector de fotos. Revisa tu conexión.")); };
      document.head.appendChild(s);
    });
  }

  function abrirImagen(archivo) {
    return new Promise(function (ok, mal) {
      var img = new Image();
      img.onload = function () { ok(img); };
      img.onerror = function () { mal(new Error("No pude abrir la imagen.")); };
      img.src = URL.createObjectURL(archivo);
    });
  }

  // Mira cada píxel: ¿tiene color (los bloques de clase) o es blanco/gris?
  // Devuelve la foto en gris para leer los días, otra en blanco y negro donde
  // las letras blancas de los bloques salen negras, y el mapa de "tiene color".
  function prepararFoto(img) {
    var escala = img.width < 1600 ? 2 : 1;            // las fotos pequeñas se leen mejor más grandes
    var W = img.width * escala, H = img.height * escala;
    var lienzo = document.createElement("canvas");
    lienzo.width = W; lienzo.height = H;
    var ctx = lienzo.getContext("2d");
    ctx.drawImage(img, 0, 0, W, H);
    var original = ctx.getImageData(0, 0, W, H);
    var gris = ctx.createImageData(W, H), letras = ctx.createImageData(W, H);
    var color = new Uint8Array(W * H);
    for (var i = 0, k = 0; k < W * H; i += 4, k++) {
      var r = original.data[i], g = original.data[i + 1], b = original.data[i + 2];
      var max = Math.max(r, g, b), min = Math.min(r, g, b);
      color[k] = max > 60 && (max - min) / max > 0.3 ? 1 : 0;
      gris.data[i] = gris.data[i + 1] = gris.data[i + 2] = 0.299 * r + 0.587 * g + 0.114 * b;
      letras.data[i] = letras.data[i + 1] = letras.data[i + 2] = color[k] ? 255 : 0;
      gris.data[i + 3] = letras.data[i + 3] = 255;
    }
    function aUrl(datos) { ctx.putImageData(datos, 0, 0); return lienzo.toDataURL("image/png"); }
    return { W: W, H: H, color: color, gris: aUrl(gris), letras: aUrl(letras) };
  }

  // Los bloques de color: zonas de píxeles de color pegados entre sí
  function buscarBloques(foto) {
    var W = foto.W, H = foto.H, color = foto.color;
    var marca = new Uint8Array(W * H), cola = new Int32Array(W * H), bloques = [];
    for (var inicio = 0; inicio < W * H; inicio++) {
      if (!color[inicio] || marca[inicio]) continue;
      var lee = 0, escribe = 0, x0 = W, x1 = 0, y0 = H, y1 = 0, total = 0;
      cola[escribe++] = inicio; marca[inicio] = 1;
      while (lee < escribe) {
        var p = cola[lee++], x = p % W, y = (p - x) / W;
        total++;
        if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
        if (x > 0 && color[p - 1] && !marca[p - 1]) { marca[p - 1] = 1; cola[escribe++] = p - 1; }
        if (x < W - 1 && color[p + 1] && !marca[p + 1]) { marca[p + 1] = 1; cola[escribe++] = p + 1; }
        if (y > 0 && color[p - W] && !marca[p - W]) { marca[p - W] = 1; cola[escribe++] = p - W; }
        if (y < H - 1 && color[p + W] && !marca[p + W]) { marca[p + W] = 1; cola[escribe++] = p + W; }
      }
      var ancho = x1 - x0 + 1, alto = y1 - y0 + 1;
      // Un bloque de clase es un rectángulo grande y casi lleno (las letras dejan huecos)
      if (ancho > 40 * W / 1200 && alto > 40 * W / 1200 && total > 0.5 * ancho * alto) {
        bloques.push({ x0: x0, x1: x1, y0: y0, y1: y1 });
      }
    }
    return bloques;
  }

  function sinTildes(t) { return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }

  // Las columnas de los días: dónde (x) está escrito cada día de la semana
  function columnasDias(resultado) {
    var mejor = [];
    lineasDe(resultado).forEach(function (l) {
      var encontrados = [];
      l.words.forEach(function (w) {
        var t = sinTildes(w.text).replace(/[^a-z]/g, "");
        DIAS.forEach(function (nombres, dia) {
          if (t && nombres.some(function (n) { return sinTildes(n) === t; })) {
            encontrados.push({ dia: dia, x: (w.bbox.x0 + w.bbox.x1) / 2, y: w.bbox.y1 });
          }
        });
      });
      if (encontrados.length > mejor.length) mejor = encontrados;
    });
    return mejor.length >= 2 ? mejor : [];
  }

  function lineasDe(resultado) {
    var lineas = [];
    (resultado.data.blocks || []).forEach(function (bloque) {
      bloque.paragraphs.forEach(function (p) { lineas = lineas.concat(p.lines); });
    });
    return lineas;
  }

  // Los números de las horas a la izquierda (8, 9, 10...) con su altura
  function etiquetasHoras(resultado, W) {
    var marcas = [];
    lineasDe(resultado).forEach(function (l) {
      l.words.forEach(function (w) {
        var n = w.text.replace(/[^\d:]/g, "").replace(/:00$/, "");
        if (/^\d{1,2}$/.test(n) && +n <= 23 && w.bbox.x1 < W * 0.15) marcas.push({ hora: +n, y: w.bbox.y0 });
      });
    });
    return marcas;
  }

  // Recta que pasa por los puntos (hora → altura en la foto), ignorando los que no cuadran
  function ajustar(puntos) {
    var usados = puntos.slice();
    for (var vuelta = 0; vuelta < 3 && usados.length >= 2; vuelta++) {
      var n = usados.length, sx = 0, sy = 0, sxx = 0, sxy = 0;
      usados.forEach(function (p) { sx += p.hora; sy += p.y; sxx += p.hora * p.hora; sxy += p.hora * p.y; });
      var div = n * sxx - sx * sx;
      if (!div) return null;
      var b = (n * sxy - sx * sy) / div, a = (sy - b * sx) / n;
      if (b <= 0) return null;
      var buenos = usados.filter(function (p) { return Math.abs(a + b * p.hora - p.y) < b * 0.25; });
      if (buenos.length === usados.length) return { a: a, b: b };
      usados = buenos;
    }
    return null;
  }

  function dos(n) { return (n < 10 ? "0" : "") + n; }
  function aHora(h) {
    var minutos = Math.round(h * 60 / 5) * 5;
    return dos(Math.floor(minutos / 60)) + ":" + dos(minutos % 60);
  }

  // Las líneas de texto de un bloque, sin la de abajo si sale cortada por el borde
  function lineasEnteras(resultado, abajo) {
    var lineas = lineasDe(resultado).filter(function (l) { return l.text.trim(); });
    var altos = lineas.map(function (l) { return l.bbox.y1 - l.bbox.y0; }).sort(function (a, b) { return a - b; });
    var normal = altos[Math.floor(altos.length / 2)] || 0;
    var ultima = lineas[lineas.length - 1];
    if (lineas.length > 1 && abajo - ultima.bbox.y1 < normal * 0.3) lineas.pop();
    return lineas.map(function (l) { return l.text.trim(); }).join("\n");
  }

  // Del texto de un bloque saca la hora de inicio (si se lee), el nombre y el aula
  var HORA = /^(\d{1,2})[:.,](\d{2})(?:\s*[-–—]\s*(\d{1,2})[:.,](\d{2}))?/;
  var AULA = /^[A-Z0-9ÁÉÍÓÚÑ]+(?:-[A-Z0-9]*)*-?$/;
  function textoDelBloque(texto) {
    var lineas = texto.split("\n").map(function (l) { return l.trim(); }).filter(Boolean);
    var datos = { nombre: "", sala: "" };
    if (lineas.length && HORA.test(lineas[0].replace(/\s/g, " "))) {
      var m = HORA.exec(lineas.shift());
      datos.desde = +m[1] + +m[2] / 60;
      if (m[3]) datos.hasta = +m[3] + +m[4] / 60;
    }
    var nombre = [], sala = [];
    lineas.forEach(function (l) {
      var palabra = l.replace(/\s+/g, "");
      if (sala.length || (AULA.test(palabra) && /[\d-]/.test(palabra) && palabra.length > 1)) sala.push(palabra);
      else nombre.push(l);
    });
    datos.nombre = nombre.join(" ").replace(/(^|\s)\|(?=\s|$)/g, "$1I").replace(/[:;]+(?=\s|$)/g, "").replace(/\s+/g, " ").replace(/\s+([,.)])/g, "$1").trim();
    // El aula: si la última parte salió cortada por abajo ("ALTANI") se quita
    var partes = sala.join("").split("-").filter(Boolean).map(function (t) { return t.replace(/^([A-Z])O$/, "$10").replace(/O(\d)$/, "0$1").replace(/O(\d\d)$/, "$1"); });
    if (partes.length > 1 && !/\d/.test(partes[partes.length - 1])) partes.pop();
    // Solo si se ve entera (la última parte tipo "AULA02"); "FCOM-P0" a medias no sirve
    var ultima = partes[partes.length - 1] || "";
    datos.sala = ultima.length >= 3 && /\d/.test(ultima) ? partes.join("-") : "";
    return datos;
  }

  // Si el nombre salió cortado ("Diseño e innovaci del producto") y ya tienes una
  // materia que encaja ("Diseño e innovación del producto"), se usa esa.
  function empiezaIgual(entera, cortada) {
    entera = entera.replace(/[^a-z0-9]/g, ""); cortada = cortada.replace(/[^a-z0-9]/g, "");
    // La última letra o dos pueden salir mal porque el borde corta la palabra
    for (var quitar = 0; quitar <= (cortada.length >= 6 ? 2 : cortada.length >= 4 ? 1 : 0); quitar++) {
      if (entera.indexOf(cortada.slice(0, cortada.length - quitar)) === 0) return true;
    }
    return false;
  }

  function completarNombre(nombre, materias) {
    var mias = sinTildes(nombre).split(/\s+/);
    var encontrada = materias.filter(function (m) {
      var suyas = sinTildes(m).split(/\s+/);
      if (suyas.length < mias.length) return false;
      return mias.every(function (w, i) { return empiezaIgual(suyas[i], w); });
    });
    // Si encajan varias, la más larga (la que tiene el nombre completo)
    encontrada.sort(function (a, b) { return b.length - a.length || (a === nombre) - (b === nombre); });
    return encontrada.length ? encontrada[0] : nombre;
  }

  function aCsv(clases) {
    function celda(t) { return '"' + String(t).replace(/"/g, '""') + '"'; }
    return "día;desde;hasta;materia;aula\n" + clases.map(function (c) {
      return [NOMBRES_DIAS[c.dia], c.desde, c.hasta, celda(c.nombre), celda(c.sala)].join(";");
    }).join("\n");
  }

  // Lee la foto y devuelve las clases encontradas
  function leerFoto(archivo, aviso, materias) {
    var Tess, foto, trabajador, columnas, horas;
    aviso("Cargando el lector de fotos…");
    return cargarTesseract().then(function (T) {
      Tess = T;
      return abrirImagen(archivo);
    }).then(function (img) {
      foto = prepararFoto(img);
      foto.bloques = buscarBloques(foto);
      return Tess.createWorker("spa", 1, OPCIONES);
    }).then(function (w) {
      trabajador = w;
      aviso("Buscando los días y las horas…");
      return w.recognize(foto.gris, {}, { blocks: true });
    }).then(function (r) {
      columnas = columnasDias(r);
      horas = etiquetasHoras(r, foto.W);
      if (!columnas.length) throw new Error("No encontré los días de la semana en la foto. Haz la captura con los días arriba.");
      var arriba = Math.max.apply(null, columnas.map(function (c) { return c.y; }));
      foto.bloques = foto.bloques.filter(function (b) { return b.y0 > arriba; });
      // Cada bloque se lee por separado, con las letras en negro sobre blanco
      var lecturas = [], cadena = trabajador.setParameters({ tessedit_pageseg_mode: "6" });
      foto.bloques.forEach(function (b, i) {
        cadena = cadena.then(function () {
          aviso("Leyendo las clases (" + (i + 1) + " de " + foto.bloques.length + ")…");
          var borde = 4;
          return trabajador.recognize(foto.letras, { rectangle: {
            left: b.x0 + borde, top: b.y0 + borde, width: b.x1 - b.x0 - 2 * borde, height: b.y1 - b.y0 - 2 * borde } },
            { blocks: true });
        }).then(function (r) { lecturas[i] = textoDelBloque(lineasEnteras(r, b.y1 - 4)); });
      });
      return cadena.then(function () { return lecturas; });
    }).then(function (lecturas) {
      trabajador.terminate();
      // La altura de cada hora: con las horas de inicio que se leyeron en los bloques
      // (lo más fiable) y si no, con los números de la izquierda.
      var puntos = [];
      foto.bloques.forEach(function (b, i) {
        if (lecturas[i].desde !== undefined) puntos.push({ hora: lecturas[i].desde, y: b.y0 });
      });
      var recta = ajustar(puntos) || ajustar(horas);
      if (!recta) throw new Error("No pude saber a qué hora empieza cada clase. Haz la captura con las horas visibles.");
      var clases = [];
      foto.bloques.forEach(function (b, i) {
        var leido = lecturas[i];
        if (!leido.nombre) return;
        var centro = (b.x0 + b.x1) / 2;
        var columna = columnas.reduce(function (a, c) { return Math.abs(c.x - centro) < Math.abs(a.x - centro) ? c : a; });
        var desde = (b.y0 - recta.a) / recta.b, hasta = (b.y1 - recta.a) / recta.b;
        // Si la hora escrita cuadra con la posición, vale más la escrita
        if (leido.desde !== undefined && Math.abs(leido.desde - desde) < 0.25) desde = leido.desde;
        if (leido.hasta !== undefined && Math.abs(leido.hasta - hasta) < 0.25) hasta = leido.hasta;
        clases.push({ dia: columna.dia, desde: aHora(desde), hasta: aHora(hasta),
                      nombre: completarNombre(leido.nombre, materias || []), sala: leido.sala });
      });
      return clases.sort(function (a, b) { return a.dia - b.dia || a.desde.localeCompare(b.desde); });
    });
  }

  window.leerFotoHorario = leerFoto;   // para las pruebas

  // ---- En la página: si eliges una imagen, se lee aquí y se enseña la lista ----
  document.querySelectorAll("form.subir-horario").forEach(function (form) {
    var campo = form.querySelector("[data-archivo]");
    var zona = form.querySelector("[data-foto-resultado]");
    form.addEventListener("submit", function (e) {
      var archivo = campo.files[0];
      if (!archivo || !/^image\//.test(archivo.type)) return;   // CSV, Excel o página: lo lee el servidor
      e.preventDefault();
      var boton = form.querySelector("button");
      boton.disabled = true;
      zona.hidden = false;
      zona.textContent = "";
      var estado = document.createElement("p");
      estado.className = "foto-estado";
      zona.appendChild(estado);
      leerFoto(archivo, function (t) { estado.textContent = t; }, JSON.parse(form.dataset.materias || "[]")).then(function (clases) {
        boton.disabled = false;
        if (!clases.length) {
          estado.textContent = "No encontré clases en la foto. Funciona mejor con una captura donde cada clase dice su hora (como pintahorarios).";
          return;
        }
        estado.textContent = "Encontré " + clases.length + " clase(s). Revisa los nombres (en fotos del móvil a veces salen cortados) y quita las que estén mal:";
        var lista = document.createElement("div");
        lista.className = "lista-eventos lista-foto";
        clases.forEach(function (c, i) {
          var fila = document.createElement("div");
          fila.className = "evento-opcion";
          var check = document.createElement("input");
          check.type = "checkbox"; check.checked = true; check.dataset.indice = i;
          check.setAttribute("aria-label", "Añadir esta clase");
          var texto = document.createElement("span");
          var nombre = document.createElement("input");
          nombre.type = "text"; nombre.value = c.nombre; nombre.className = "foto-nombre"; nombre.dataset.nombre = i;
          var detalle = document.createElement("small");
          detalle.textContent = NOMBRES_DIAS[c.dia] + " · " + c.desde + "–" + c.hasta + (c.sala ? " · " + c.sala : "");
          texto.appendChild(nombre); texto.appendChild(detalle);
          fila.appendChild(check); fila.appendChild(texto);
          lista.appendChild(fila);
        });
        zona.appendChild(lista);
        var anadir = document.createElement("button");
        anadir.type = "button";
        anadir.className = "boton boton-primario boton-chico";
        anadir.textContent = "Añadir al horario";
        anadir.addEventListener("click", function () {
          var elegidas = clases.filter(function (c, i) {
            c.nombre = lista.querySelector('[data-nombre="' + i + '"]').value.trim() || c.nombre;
            return lista.querySelector('[data-indice="' + i + '"]').checked;
          });
          if (!elegidas.length) return;
          var datos = new FormData();
          datos.append("archivo", new Blob(["﻿" + aCsv(elegidas)], { type: "text/csv" }), "foto.csv");
          anadir.disabled = true;
          fetch(form.action, { method: "POST", body: datos, credentials: "same-origin" })
            .then(function (r) { window.location.href = r.url || form.action; });
        });
        zona.appendChild(anadir);
      }).catch(function (error) {
        boton.disabled = false;
        estado.textContent = error.message || "No pude leer la foto.";
      });
    });
  });
})();
