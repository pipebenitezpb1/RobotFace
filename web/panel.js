// Panel en vivo: enciende y apaga el robot, dibuja su boca igual que la pantalla de hablar.py,
// muestra la cámara con las caras, lo que escucha y responde, y manda expresiones y escaneos.
(() => {
  const $ = id => document.getElementById(id);
  const API = (ruta, cuerpo) => fetch(ruta, {
    method: "POST", headers: { "X-Robot": "1", "Content-Type": "application/json" },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  }).then(r => r.json()).catch(() => ({ error: "sin servidor" }));

  // ---------- Boca (copia de dibujar_forma_boca de hablar.py) ----------
  const lienzo = $("boca"), g = lienzo.getContext("2d");
  const forma = { abierta: 0, ancho: 1, sonrisa: .3, lado: 0, ladeo: 0 };
  let objetivo = { ...forma }, vivo = { modo: "apagado", dormida: false, silenciado: false, t: 0 };
  const COLORES_MODO = { iniciando: "#5a5a6e", escuchando: "#46beff", oyendo: "#5affaa", pensando: "#aa78ff", hablando: "#ff8c28", error: "#ff3c3c", apagado: "#55534a" };
  const NOMBRE_MODO = { iniciando: "partiendo", escuchando: "escuchando", oyendo: "te oye", pensando: "pensando", hablando: "hablando", error: "error", apagado: "apagado" };

  function curva(p0, p1, p2, n = 40) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const u = i / (n - 1);
      out.push([(1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0], (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]]);
    }
    return out;
  }
  function trazo(pts) { g.beginPath(); g.moveTo(...pts[0]); for (const p of pts.slice(1)) g.lineTo(...p); }

  function dibujarBoca(ancho, alto, f, labios) {
    const W = Math.min(ancho * .45, alto * 1.1) * f.ancho;
    const cx = ancho / 2 + f.lado * ancho, cy = alto * .45;
    const abierta = W * .38 * f.abierta, subida = W * .16 * f.sonrisa, ladeo = W * .12 * f.ladeo;
    const izq = [cx - W / 2, cy - subida + ladeo], der = [cx + W / 2, cy - subida - ladeo];
    const grosor = Math.max(8, W * .055);
    g.lineWidth = grosor; g.lineCap = "round"; g.lineJoin = "round"; g.strokeStyle = labios;
    if (abierta < 3) { trazo(curva(izq, [cx, cy + subida * 1.5], der)); g.stroke(); return; }
    const arriba = curva(izq, [cx, cy - abierta * .7 + subida * .6], der);
    const abajo = curva(der, [cx, cy + abierta * 2 + subida * 1.4], izq);
    const contorno = arriba.concat(abajo);
    g.save();
    trazo(contorno); g.closePath(); g.fillStyle = "rgb(55,12,22)"; g.fill(); g.clip();
    const altoDientes = Math.min(abierta * .28, W * .06);
    trazo(arriba.concat(arriba.slice().reverse().map(([x, y]) => [x, y + altoDientes]))); g.fillStyle = "rgb(245,242,235)"; g.fill();
    if (abierta > W * .1) {
      g.beginPath(); g.ellipse(cx, cy + abierta * 1.15 + subida * .5, W * .275, abierta * .5, 0, 0, Math.PI * 2);
      g.fillStyle = "rgb(225,85,105)"; g.fill();
    }
    g.restore();
    trazo(arriba); g.stroke(); trazo(abajo); g.stroke();
  }

  const CICLO = 3.6;
  function zetas(ancho, alto, t) {
    const cx = ancho / 2, cy = alto * .45, W = Math.min(ancho * .45, alto * 1.1);
    for (let k = 0; k < 5; k++) {
      const f = (t / (CICLO * 2.5) + k / 5) % 1, tam = 14 + 40 * f;
      g.globalAlpha = Math.min(1, f * 4) * (1 - f);
      g.fillStyle = "rgb(255,125,30)"; g.font = `bold ${tam}px Helvetica, sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
      g.fillText(k % 2 ? "z" : "Z", cx + W * .42 + f * W * .45 + 10 * Math.sin(t * 2 + k), cy - W * .05 - f * alto * .38);
    }
    g.globalAlpha = 1;
  }

  const inicio = performance.now();
  function cuadro() {
    const t = (performance.now() - inicio) / 1000;
    const encendido = performance.now() / 1000 - vivo.t < 2;
    if (!encendido) objetivo = { abierta: 0, ancho: .7, sonrisa: 0, lado: 0, ladeo: 0 };
    for (const k in forma) forma[k] += (objetivo[k] - forma[k]) * .45;
    g.fillStyle = "#000"; g.fillRect(0, 0, lienzo.width, lienzo.height);
    const alto = lienzo.height - 70;
    dibujarBoca(lienzo.width, alto, forma, !encendido ? "#3a3830" : vivo.silenciado ? "rgb(120,120,120)" : "rgb(255,125,30)");
    if (encendido && vivo.dormida) zetas(lienzo.width, alto, t);
    requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);

  // ---------- Datos en vivo ----------
  let ultimaCamara = 0, cargandoCamara = false;
  const camara = $("camara");
  camara.onload = () => { cargandoCamara = false; $("camara-vacia").hidden = true; camara.hidden = false; };
  camara.onerror = () => { cargandoCamara = false; };
  setInterval(() => {   // la cámara se pide sola, de a una imagen a la vez
    if (!camaraActiva || cargandoCamara) return;
    cargandoCamara = true; camara.src = "/api/camara.jpg?" + Date.now();
  }, 150);
  let camaraActiva = false;

  function texto(e, s) { if (e.textContent !== s) e.textContent = s; }

  function alBoca(d) {
    vivo = { ...d, t: performance.now() / 1000 };
    objetivo = d.forma;
    const m = $("modo");
    m.querySelector("i").style.background = d.dormida ? "#ff7d1e" : (COLORES_MODO[d.modo] || "#ccc");
    texto(m.querySelector("span"), d.dormida ? "durmiendo" : d.silenciado ? "silenciado" : (NOMBRE_MODO[d.modo] || d.modo));
    texto($("sub-robot"), d.robot || "");
    texto($("sub-tu"), d.tu || "");
    const pos = v => Math.sqrt(Math.min(1, Math.max(0, v / .3))) * 100;
    const nivel = $("mic-nivel");
    nivel.style.width = pos(d.mic) + "%";
    nivel.classList.toggle("voz", d.mic > d.umbral);
    $("mic-umbral").style.left = pos(d.umbral) + "%";
  }

  const FUENTE = { "cara+ropa": "cara + ropa", cara: "cara", ropa: "ropa" };
  let escaneoVisto = null;
  function alEstado(e) {
    const corre = e.corriendo.seguir || e.corriendo.hablar;
    const luz = $("luz-general");
    luz.classList.toggle("encendido", corre && !e.iniciando);
    luz.classList.toggle("partiendo", !!e.iniciando);
    texto($("texto-general"), e.iniciando ? "Encendiendo…" : corre ? (e.corriendo.seguir && e.corriendo.hablar ? "Encendido" : e.corriendo.seguir ? "Solo ojos" : "Solo voz") : "Apagado");
    $("btn-encender").textContent = corre ? "Reiniciar" : "Encender robot";
    $("btn-apagar").disabled = !corre;
    if (!e.corriendo.hablar) { texto($("modo").querySelector("span"), "apagado"); $("modo").querySelector("i").style.background = COLORES_MODO.apagado; texto($("sub-robot"), ""); texto($("sub-tu"), ""); }

    camaraActiva = !!e.camara;
    if (!camaraActiva) { camara.hidden = true; $("camara-vacia").hidden = false; }
    const s = e.seguir;
    texto($("estado-sueno"), !s ? "" : s.escaneo ? "Escaneando" : s.dormido ? "Durmiendo · zzz" : s.caras.length ? "Despierto" : "Buscando caras");

    const lista = $("caras");
    const filas = (s?.caras || []).map(c => `<li class="${c.mirando ? "mirando" : ""}"><span><b>${c.nombre ? esc(c.nombre) : "Cara " + c.id}</b>${c.nombre ? ` <small>por ${FUENTE[c.fuente] || c.fuente} · ${c.nota.toFixed(2)}</small>` : " <small>desconocida</small>"}</span><small>${c.mirando ? "la mira" : ""}${c.habla > .3 ? " · habla" : ""}</small></li>`).join("");
    if (lista.innerHTML !== filas) lista.innerHTML = filas;
    texto($("conocidos"), s?.conocidos?.length ? "Reconoce por la cara a: " + s.conocidos.join(", ") : "");

    // Escaneo
    const es = s?.escaneo;
    $("escaneo-progreso").hidden = !es;
    $("form-escaneo").hidden = !!es;
    if (es) {
      $("pasos-escaneo").innerHTML = Array.from({ length: es.total }, (_, i) => `<i class="${i < es.paso ? "hecho" : i === es.paso ? "ahora" : ""}"></i>`).join("");
      texto($("escaneo-texto"), `${es.nombre}: ${es.instruccion} (${es.capturas} de ${es.total} capturas)`);
    } else if (s?.aviso) texto($("conocidos"), s.aviso);
    escaneoVisto = es;

    // Conversación
    const conv = $("conversacion");
    const html = e.conversacion.length ? e.conversacion.map(m => `<li class="${m.quien}">${esc(m.texto)}</li>`).join("") : '<li class="vacio">Todavía nadie habla.</li>';
    if (conv.innerHTML !== html) { conv.innerHTML = html; conv.scrollTop = conv.scrollHeight; }
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]); }

  function conectar() {
    const ev = new EventSource("/api/vivo");
    ev.addEventListener("boca", m => alBoca(JSON.parse(m.data)));
    ev.addEventListener("estado", m => { $("sin-servidor").hidden = true; alEstado(JSON.parse(m.data)); });
    ev.onerror = () => {
      ev.close();
      fetch("/api/estado").then(r => { if (!r.ok) throw 0; }).catch(() => { $("sin-servidor").hidden = false; });
      setTimeout(conectar, 2000);
    };
  }
  conectar();

  // ---------- Botones ----------
  $("btn-encender").onclick = async () => {
    $("luz-general").classList.add("partiendo"); texto($("texto-general"), "Encendiendo…");
    const r = await API("/api/iniciar"); if (r.error) $("sin-servidor").hidden = false;
  };
  $("btn-apagar").onclick = () => API("/api/detener");
  const fichas = $("fichas-robot");
  for (let n = 1; n < Ojos.EXPRESIONES.length; n++) {
    if (n === 15 || n === 16) continue;   // dormir y despertar los decide la cámara
    const b = document.createElement("button");
    b.className = "ficha"; b.textContent = Ojos.EXPRESIONES[n].n;
    b.onclick = () => { API("/api/expresion?n=" + n); Ojos.hacer(n); };
    fichas.appendChild(b);
  }
  $("form-escaneo").onsubmit = ev => {
    ev.preventDefault();
    const nombre = $("nombre-escaneo").value.trim();
    if (!nombre) return $("nombre-escaneo").focus();
    API("/api/escanear", { nombre }); $("nombre-escaneo").value = "";
  };
  $("btn-cancelar-escaneo").onclick = () => API("/api/cancelar_escaneo");
})();
