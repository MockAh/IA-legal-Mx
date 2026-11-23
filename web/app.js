/* Asistente Legal Mexicano — cliente del frontend
   Conversa con main.py: /api/estado, /api/catalogo, /api/consulta y /api/consulta/stream.
   La interfaz es bilingüe; las respuestas del agente llegan del backend en español. */

(function () {
  "use strict";

  /* ══ Diccionario ═══════════════════════════════════════════
     Clave → [español, inglés]. Las claves con HTML se marcan en
     el documento con data-i18n-html. */

  var DICT = {
    "marca.titulo":   ["Asistente Legal Mexicano", "Mexican Legal Assistant"],
    "marca.lema":     ["Impulsado por Inteligencia Artificial", "Powered by Artificial Intelligence"],
    "idioma.grupo":   ["Idioma de la interfaz", "Interface language"],
    "nav.secciones":  ["Secciones del agente", "Agent sections"],

    "tab.cita":          ["Cita Precisa", "Exact Citation"],
    "tab.cita.sub":      ["Recuperación literal", "Literal retrieval"],
    "tab.razon":         ["Razonamiento Jurídico", "Legal Reasoning"],
    "tab.razon.sub":     ["Síntesis fundada", "Grounded synthesis"],
    "tab.catalogo":      ["Catálogo FAISS", "FAISS Catalog"],
    "tab.catalogo.sub":  ["Acervo indexado", "Indexed corpus"],

    "modo.fijo":       ["Modo fijo de esta pestaña", "Fixed mode for this tab"],
    "candado.fijo":    ["Fijo en esta pestaña", "Fixed in this tab"],
    "candado.stream":  ["Respuesta progresiva", "Progressive response"],
    "salida.titulo":   ["Respuesta", "Response"],

    "base.legend":    ["Base de datos", "Database"],
    "base.fce":       ["FCE", "FCE"],
    "base.tramites":  ["Trámites SEGOB", "SEGOB Procedures"],
    "base.general":   ["General", "General"],

    "btn.consultar":  ["Consultar", "Search"],
    "btn.analizar":   ["Analizar", "Analyze"],

    "cita.h2":   ["Qué hace Cita Precisa", "What Exact Citation does"],
    "cita.p1":   ["Devuelve el <strong>texto literal</strong> de un artículo, tal como está registrado en el acervo. No interpreta, no resume y no agrega comentario: localiza la norma exacta y la entrega con su ley, su número de artículo y su archivo de origen.",
                  "It returns the <strong>literal text</strong> of an article exactly as recorded in the corpus. It does not interpret, summarize or comment: it locates the precise provision and delivers it with its law, article number and source file."],
    "cita.p2":   ["Úsalo cuando ya sabes qué citar y necesitas el texto íntegro para un escrito, un dictamen o una audiencia.",
                  "Use it when you already know what to cite and need the full text for a brief, an opinion or a hearing."],
    "cita.paso1": ["El modelo extrae de tu consulta el <code>titulo_documento</code> y el <code>Articulo</code>.",
                   "The model extracts <code>titulo_documento</code> and <code>Articulo</code> from your query."],
    "cita.paso2": ["FAISS resuelve el nombre coloquial de la ley contra el título exacto del acervo.",
                   "FAISS matches the colloquial name of the law against the exact title in the corpus."],
    "cita.paso3": ["Chroma filtra por ley, artículo y <code>Transitorio</code>, y regresa el párrafo completo.",
                   "Chroma filters by law, article and <code>Transitorio</code>, and returns the full paragraph."],
    "cita.modo":  ["Modo: Cita Precisa", "Mode: Exact Citation"],
    "cita.ph":    ["Artículo 16 de la Constitución Política de los Estados Unidos Mexicanos",
                   "Article 16 of the Political Constitution of the United Mexican States"],
    "cita.sug1":  ["Artículo 123 de la Ley Federal del Trabajo", "Article 123 of the Federal Labor Law"],
    "cita.sug2":  ["Artículo 14 de la Constitución", "Article 14 of the Constitution"],
    "cita.vacia": ["Escribe la ley y el artículo que necesitas citar.",
                   "Type the law and article you need to cite."],

    "razon.h2":  ["Qué hace Razonamiento Jurídico", "What Legal Reasoning does"],
    "razon.p1":  ["Recupera los fragmentos normativos pertinentes y redacta una <strong>respuesta argumentada</strong> en tiempo real, citando la fuente de cada afirmación. Es el modo para preguntas abiertas: procedencia, requisitos, plazos, conflictos entre normas.",
                  "It retrieves the relevant statutory passages and drafts a <strong>reasoned answer</strong> in real time, citing the source of every claim. This is the mode for open questions: standing, requirements, deadlines, conflicts between rules."],
    "razon.p2":  ["La redacción se apoya solo en lo recuperado del acervo. Si la normativa cargada no alcanza para responder, lo dice en lugar de completar por su cuenta.",
                  "The drafting rests only on what was retrieved from the corpus. If the loaded legislation is not enough to answer, it says so instead of filling the gap on its own."],
    "razon.paso1": ["Búsqueda híbrida: filtro exacto por ley y artículo, más búsqueda semántica.",
                    "Hybrid search: exact filter by law and article, plus semantic search."],
    "razon.paso2": ["Se arma el contexto con los fragmentos únicos y su metadato de ley.",
                    "The context is assembled from the unique passages and their law metadata."],
    "razon.paso3": ["El modelo redacta progresivamente y cierra con las fuentes consultadas.",
                    "The model drafts progressively and closes with the sources it consulted."],
    "razon.modo":  ["Modo: Razonamiento Jurídico", "Mode: Legal Reasoning"],
    "razon.ph":    ["¿Qué requisitos debe cumplir un acto de molestia para ser constitucionalmente válido?",
                    "What requirements must an intrusive official act meet to be constitutionally valid?"],
    "razon.sug1":  ["¿Qué dice el artículo 16 constitucional sobre los actos de molestia de la autoridad?",
                    "What does constitutional article 16 say about intrusive acts by authorities?"],
    "razon.sug2":  ["¿Cuál es el plazo para responder una solicitud de información?",
                    "What is the deadline to answer a request for information?"],
    "razon.vacia": ["Plantea tu pregunta en lenguaje natural.", "Ask your question in plain language."],

    "cat.rotulo":       ["Memoria semántica", "Semantic memory"],
    "cat.h2":           ["Qué contiene el Catálogo FAISS", "What the FAISS Catalog holds"],
    "cat.p1":           ["Es el inventario completo de la jurisdicción cargada en el índice de títulos: toda ley, reglamento o estatuto que el agente puede citar. Se construye leyendo <code>metadata_titulos_leyes.pkl</code> y agrupando por la carpeta de origen dentro de <code>legislacion-mx/</code>.",
                         "It is the full inventory of the jurisdiction loaded into the title index: every law, regulation or statute the agent can cite. It is built by reading <code>metadata_titulos_leyes.pkl</code> and grouping by the source folder inside <code>legislacion-mx/</code>."],
    "cat.p2":           ["Si una norma no aparece aquí, el agente no la tiene y lo dirá en lugar de aproximarla. Es la forma rápida de verificar cobertura antes de confiar una consulta al sistema.",
                         "If a provision is not listed here, the agent does not have it and will say so rather than approximate it. This is the quick way to check coverage before trusting the system with a query."],
    "cat.tira.leyes":    ["Leyes indexadas", "Indexed laws"],
    "cat.tira.materias": ["Materias", "Subject areas"],
    "cat.tira.acervos":  ["Acervos en línea", "Corpora online"],
    "cat.tira.vector":   ["Dimensión del vector", "Vector dimension"],
    "cat.buscar.label":  ["Buscar ley", "Search law"],
    "cat.buscar.ph":     ["Buscar por nombre de ley, reglamento o código…",
                          "Search by name of law, regulation or code…"],
    "cat.sin":           ["Ninguna norma del índice coincide con esa búsqueda.",
                          "No provision in the index matches that search."],
    "cat.cargando":      ["Leyendo el índice de títulos…", "Reading the title index…"],
    "cat.error":         ["No se pudo leer el catálogo: ", "The catalog could not be read: "],
    "cat.todas":         ["Todas", "All"],
    "cat.titulos":       ["títulos", "titles"],

    "pie": ["Las respuestas se construyen únicamente con la normativa cargada en el acervo. Verifica siempre contra la publicación oficial en el <b>Diario Oficial de la Federación</b> antes de usarlas en un escrito con efectos jurídicos.",
            "Answers are built only from the legislation loaded into the corpus. Always verify against the official publication in the <b>Diario Oficial de la Federación</b> before relying on them in a document with legal effect."],

    /* Estado del sistema */
    "est.faiss.ok":    ["Índice FAISS activo", "FAISS index active"],
    "est.faiss.no":    ["Índice FAISS ausente", "FAISS index missing"],
    "est.acervos":     ["{a} de {b} acervos", "{a} of {b} corpora"],
    "est.modelo.ok":   ["Modelo e5 en disco", "e5 model on disk"],
    "est.modelo.no":   ["Modelo e5 remoto", "e5 model remote"],
    "est.sincontacto": ["Sin contacto con el servidor", "No contact with the server"],
    "base.sindatos":   ["sin datos en el servidor", "no data on this server"],
    "base.faltan":     ["Acervos faltantes: ", "Missing corpora: "],

    /* Mensajes de proceso y error */
    "proc.cita":    ["Localizando la norma en el acervo…", "Locating the provision in the corpus…"],
    "proc.razon":   ["Preparando la búsqueda…", "Preparing the search…"],
    "err.consulta": ["**No se pudo completar la consulta.**\n\n", "**The query could not be completed.**\n\n"],
    "err.analisis": ["**No se pudo completar el análisis.**\n\n", "**The analysis could not be completed.**\n\n"],
    "err.red":      ["**Fallo de red.**\n\n", "**Network failure.**\n\n"],

    /* Materias del catálogo: el backend las manda en español */
    "mat.basic":         ["Legislación Básica", "Core Legislation"],
    "mat.FCE":           ["Fondo de Cultura Económica", "Fondo de Cultura Económica"],
    "mat.segob":         ["Secretaría de Gobernación", "Ministry of the Interior"],
    "mat.Transparencia": ["Transparencia", "Transparency"],
    "mat.Tres_Poderes":  ["Tres Poderes", "Branches of Government"],
    "mat.Otros":         ["Otros", "Other"]
  };

  var IDIOMAS = ["es", "en"];
  var idioma = "es";

  function t(clave) {
    var par = DICT[clave];
    if (!par) return clave;
    return par[idioma === "en" ? 1 : 0];
  }

  function leerIdiomaGuardado() {
    try {
      var g = localStorage.getItem("idioma");
      if (IDIOMAS.indexOf(g) !== -1) return g;
    } catch (e) { /* almacenamiento bloqueado */ }
    return (navigator.language || "es").toLowerCase().indexOf("en") === 0 ? "en" : "es";
  }

  function aplicarIdioma() {
    document.documentElement.lang = idioma;

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      el.innerHTML = t(el.dataset.i18nHtml);
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
      el.placeholder = t(el.dataset.i18nPh);
    });
    document.querySelectorAll("[data-i18n-label]").forEach(function (el) {
      el.setAttribute("aria-label", t(el.dataset.i18nLabel));
    });

    document.querySelectorAll(".lengua").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.idioma === idioma ? "true" : "false");
    });

    // Lo que se dibujó desde JS hay que repintarlo con el idioma nuevo.
    if (ultimoEstado) pintarEstadoSistema(ultimoEstado);
    if (catalogoCargado) {
      pintarMaterias();
      pintarCatalogo();
    }
  }

  function cambiarIdioma(nuevo) {
    if (IDIOMAS.indexOf(nuevo) === -1 || nuevo === idioma) return;
    idioma = nuevo;
    try { localStorage.setItem("idioma", nuevo); } catch (e) { /* sin persistencia */ }
    aplicarIdioma();
  }

  document.querySelectorAll(".lengua").forEach(function (b) {
    b.addEventListener("click", function () { cambiarIdioma(b.dataset.idioma); });
  });

  /* ══ Utilidades ════════════════════════════════════════════ */

  function render(markdown) {
    if (window.marked && typeof window.marked.parse === "function") {
      return window.marked.parse(markdown, { breaks: true, gfm: true });
    }
    var escapado = markdown.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return "<p>" + escapado.replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>") + "</p>";
  }

  function pintarRespuesta(nodo, markdown, opciones) {
    // Sin esto, cambiar de idioma borraría la respuesta y repondría el texto vacío.
    nodo.removeAttribute("data-i18n");
    nodo.classList.remove("vacia");
    nodo.classList.add("md");
    nodo.innerHTML = render(markdown);
    if (opciones && opciones.enCurso) {
      var cursor = document.createElement("span");
      cursor.className = "cursor";
      cursor.setAttribute("aria-hidden", "true");
      nodo.appendChild(cursor);
    }
  }

  function pintarEstado(nodo, texto, conHilo) {
    if (!texto) { nodo.textContent = ""; return; }
    nodo.innerHTML = "";
    var caja = document.createElement("div");
    caja.className = "aviso";
    caja.setAttribute("role", "status");
    if (conHilo) {
      var hilo = document.createElement("span");
      hilo.className = "hilo";
      caja.appendChild(hilo);
    }
    var s = document.createElement("span");
    s.textContent = texto.replace(/\*\*/g, "").trim();
    caja.appendChild(s);
    nodo.appendChild(caja);
  }

  function normalizar(s) {
    return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  /* ══ Pestañas ══════════════════════════════════════════════ */

  var tabs = Array.prototype.slice.call(document.querySelectorAll(".pestana"));

  function activar(tab) {
    tabs.forEach(function (t2) {
      var sel = t2 === tab;
      t2.setAttribute("aria-selected", sel ? "true" : "false");
      t2.tabIndex = sel ? 0 : -1;
      document.getElementById(t2.getAttribute("aria-controls")).hidden = !sel;
    });
    if (tab.id === "t-catalogo" && !catalogoCargado) cargarCatalogo();
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () { activar(tab); });
    tab.addEventListener("keydown", function (e) {
      var i = tabs.indexOf(tab), n = null;
      if (e.key === "ArrowRight") n = tabs[(i + 1) % tabs.length];
      if (e.key === "ArrowLeft") n = tabs[(i - 1 + tabs.length) % tabs.length];
      if (n) { e.preventDefault(); activar(n); n.focus(); }
    });
  });

  /* ══ Selección de base ═════════════════════════════════════ */

  function baseActiva(grupo) {
    var sel = document.querySelector('[data-chips="' + grupo + '"] .chip[aria-pressed="true"]');
    return sel ? sel.dataset.base : "GENERAL";
  }

  document.querySelectorAll(".chips").forEach(function (grupo) {
    grupo.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip || chip.disabled) return;
      grupo.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      chip.setAttribute("aria-pressed", "true");
    });
  });

  document.querySelectorAll(".sugerencia").forEach(function (b) {
    b.addEventListener("click", function () {
      var area = b.closest(".campo").querySelector("textarea");
      area.value = b.textContent.trim();
      area.focus();
    });
  });

  /* ══ Estado del sistema ════════════════════════════════════ */

  var ultimoEstado = null;

  function pastilla(clase, texto) {
    var s = document.createElement("span");
    s.className = "pastilla";
    var p = document.createElement("span");
    p.className = "punto " + clase;
    s.appendChild(p);
    s.appendChild(document.createTextNode(texto));
    return s;
  }

  function pintarEstadoSistema(est) {
    var barra = document.getElementById("estado-sistema");
    barra.innerHTML = "";

    var claves = Object.keys(est.acervos);
    var vivos = claves.filter(function (k) { return est.acervos[k].disponible; });
    document.getElementById("n-acervos").textContent = vivos.length + " / " + claves.length;

    var faissOk = est.faiss.indice && est.faiss.metadata;
    barra.appendChild(pastilla(faissOk ? "ok" : "falla", t(faissOk ? "est.faiss.ok" : "est.faiss.no")));
    barra.appendChild(pastilla(
      vivos.length === claves.length ? "ok" : (vivos.length ? "parcial" : "falla"),
      t("est.acervos").replace("{a}", vivos.length).replace("{b}", claves.length)));
    barra.appendChild(pastilla(est.modelo.cacheado_en_disco ? "ok" : "parcial",
      t(est.modelo.cacheado_en_disco ? "est.modelo.ok" : "est.modelo.no")));

    // Bases sin datos: deshabilitadas. Incompletas: punto ámbar.
    document.querySelectorAll(".chip[data-base]").forEach(function (chip) {
      var info = est.bases[chip.dataset.base];
      if (!info) return;
      var sub = chip.querySelector(".sub-base");
      if (!info.disponible) {
        chip.disabled = true;
        chip.setAttribute("aria-pressed", "false");
        if (!sub.dataset.original) sub.dataset.original = sub.textContent;
        sub.textContent = t("base.sindatos");
        chip.title = t("base.faltan") + info.faltantes.join(", ");
      } else if (!info.completa) {
        chip.classList.add("parcial");
        chip.title = t("base.faltan") + info.faltantes.join(", ");
      }
    });

    document.querySelectorAll(".chips").forEach(function (grupo) {
      if (grupo.querySelector('.chip[aria-pressed="true"]')) return;
      var libre = grupo.querySelector(".chip:not(:disabled)");
      if (libre) libre.setAttribute("aria-pressed", "true");
    });
  }

  function cargarEstado() {
    fetch("/api/estado").then(function (r) { return r.json(); }).then(function (est) {
      ultimoEstado = est;
      pintarEstadoSistema(est);
    }).catch(function () {
      var barra = document.getElementById("estado-sistema");
      barra.innerHTML = "";
      barra.appendChild(pastilla("falla", t("est.sincontacto")));
    });
  }

  /* ══ Cita Precisa ══════════════════════════════════════════ */

  var btnCita = document.getElementById("btn-cita");

  btnCita.addEventListener("click", function () {
    var area = document.getElementById("q-cita");
    var query = area.value.trim();
    var salida = document.getElementById("salida-cita");
    var estado = document.getElementById("estado-cita");

    if (!query) { area.focus(); return; }

    document.getElementById("eco-cita").textContent = query;
    btnCita.disabled = true;
    pintarEstado(estado, t("proc.cita"), true);
    salida.classList.add("vacia");
    salida.textContent = "";

    fetch("/api/consulta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, base: baseActiva("cita") })
    })
      .then(function (r) { return r.json(); })
      .then(function (datos) {
        pintarEstado(estado, "");
        if (datos.ok) pintarRespuesta(salida, datos.markdown);
        else pintarRespuesta(salida, t("err.consulta") + datos.error);
      })
      .catch(function (e) {
        pintarEstado(estado, "");
        pintarRespuesta(salida, t("err.red") + "`" + e.message + "`");
      })
      .finally(function () { btnCita.disabled = false; });
  });

  /* ══ Razonamiento Jurídico (SSE) ═══════════════════════════ */

  var btnRazon = document.getElementById("btn-razon");

  btnRazon.addEventListener("click", function () {
    var area = document.getElementById("q-razon");
    var query = area.value.trim();
    var salida = document.getElementById("salida-razon");
    var estado = document.getElementById("estado-razon");

    if (!query) { area.focus(); return; }

    document.getElementById("eco-razon").textContent = query;
    btnRazon.disabled = true;
    pintarEstado(estado, t("proc.razon"), true);
    salida.classList.add("vacia");
    salida.textContent = "";

    fetch("/api/consulta/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, base: baseActiva("razon") })
    }).then(function (respuesta) {
      if (!respuesta.ok || !respuesta.body) throw new Error("HTTP " + respuesta.status);

      var lector = respuesta.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";

      function quitarCursor() {
        var cursor = salida.querySelector(".cursor");
        if (cursor) cursor.remove();
      }

      function procesar(evento) {
        if (evento.tipo === "estado") {
          // Viene del backend, en español, con el progreso real de la búsqueda.
          pintarEstado(estado, evento.contenido, true);
        } else if (evento.tipo === "texto") {
          // Cada evento trae el texto ACUMULADO: se reemplaza, no se concatena.
          pintarEstado(estado, "");
          pintarRespuesta(salida, evento.contenido, { enCurso: true });
        } else if (evento.tipo === "error") {
          pintarEstado(estado, "");
          pintarRespuesta(salida, t("err.analisis") + evento.contenido);
        } else if (evento.tipo === "fin") {
          pintarEstado(estado, "");
          quitarCursor();
        }
      }

      function leer() {
        return lector.read().then(function (res) {
          if (res.done) {
            quitarCursor();
            pintarEstado(estado, "");
            btnRazon.disabled = false;
            return;
          }
          buffer += decoder.decode(res.value, { stream: true });
          var bloques = buffer.split("\n\n");
          buffer = bloques.pop();
          bloques.forEach(function (bloque) {
            var linea = bloque.split("\n").find(function (l) { return l.indexOf("data: ") === 0; });
            if (!linea) return;
            try { procesar(JSON.parse(linea.slice(6))); } catch (e) { /* bloque parcial */ }
          });
          return leer();
        });
      }

      return leer();
    }).catch(function (e) {
      pintarEstado(estado, "");
      pintarRespuesta(salida, t("err.red") + "`" + e.message + "`");
      btnRazon.disabled = false;
    });
  });

  /* ══ Catálogo FAISS ════════════════════════════════════════ */

  var catalogoCargado = false;
  var MATERIAS = [];
  var filtroMateria = "todas";
  var filtroTexto = "";

  var contenedor = document.getElementById("lista-acervos");
  var vacio = document.getElementById("sin-resultados");
  var barraMaterias = document.getElementById("materias");

  function etiquetaMateria(m) {
    // El backend manda la etiqueta en español; si conocemos la clave, la traducimos.
    return DICT["mat." + m.clave] ? t("mat." + m.clave) : m.etiqueta;
  }

  function cargarCatalogo() {
    catalogoCargado = true;
    contenedor.innerHTML = '<p class="vacio">' + t("cat.cargando") + "</p>";

    fetch("/api/catalogo").then(function (r) { return r.json(); }).then(function (cat) {
      if (!cat.disponible) {
        contenedor.innerHTML = "";
        vacio.hidden = false;
        vacio.removeAttribute("data-i18n");
        vacio.textContent = cat.mensaje;
        return;
      }
      MATERIAS = cat.materias;
      document.getElementById("n-total").textContent = cat.total;
      document.getElementById("n-materias").textContent = cat.materias.length;
      pintarMaterias();
      pintarCatalogo();
    }).catch(function (e) {
      contenedor.innerHTML = "";
      vacio.hidden = false;
      vacio.removeAttribute("data-i18n");
      vacio.textContent = t("cat.error") + e.message;
    });
  }

  function botonMateria(valor, etiqueta) {
    var b = document.createElement("button");
    b.className = "materia";
    b.type = "button";
    b.textContent = etiqueta;
    b.setAttribute("aria-pressed", valor === filtroMateria ? "true" : "false");
    b.addEventListener("click", function () {
      filtroMateria = valor;
      barraMaterias.querySelectorAll(".materia").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      b.setAttribute("aria-pressed", "true");
      pintarCatalogo();
    });
    return b;
  }

  function pintarMaterias() {
    barraMaterias.innerHTML = "";
    barraMaterias.appendChild(botonMateria("todas", t("cat.todas")));
    MATERIAS.forEach(function (m) {
      barraMaterias.appendChild(botonMateria(m.clave, etiquetaMateria(m)));
    });
  }

  function pintarCatalogo() {
    contenedor.textContent = "";
    var texto = normalizar(filtroTexto.trim());
    var hubo = 0;

    MATERIAS.forEach(function (m) {
      if (filtroMateria !== "todas" && filtroMateria !== m.clave) return;
      var items = m.titulos.filter(function (titulo) {
        return !texto || normalizar(titulo).indexOf(texto) !== -1;
      });
      if (!items.length) return;
      hubo += items.length;

      var sec = document.createElement("section");
      sec.className = "acervo";

      var cab = document.createElement("div");
      cab.className = "acervo-cabeza";
      var h3 = document.createElement("h3");
      h3.textContent = etiquetaMateria(m);
      var hr = document.createElement("hr");
      var em = document.createElement("em");
      em.textContent = String(items.length).padStart(2, "0") + " " + t("cat.titulos");
      cab.appendChild(h3); cab.appendChild(hr); cab.appendChild(em);

      var ul = document.createElement("ul");
      ul.className = "leyes";
      items.forEach(function (titulo) {
        var li = document.createElement("li");
        var i = document.createElement("i"); i.textContent = "§";
        var sp = document.createElement("span"); sp.textContent = titulo;
        li.appendChild(i); li.appendChild(sp);
        ul.appendChild(li);
      });

      sec.appendChild(cab); sec.appendChild(ul);
      contenedor.appendChild(sec);
    });

    vacio.hidden = hubo > 0;
    if (!hubo) vacio.textContent = t("cat.sin");
  }

  document.getElementById("buscar-ley").addEventListener("input", function (e) {
    filtroTexto = e.target.value;
    if (catalogoCargado) pintarCatalogo();
  });

  /* ══ Arranque ══════════════════════════════════════════════ */

  idioma = leerIdiomaGuardado();
  aplicarIdioma();
  cargarEstado();
})();
