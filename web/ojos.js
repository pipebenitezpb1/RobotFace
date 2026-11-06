// Ojos interactivos: una versión en pantalla del EyeMech. Miran el cursor, parpadean sincronizados,
// hacen las 16 expresiones del Arduino (mismos nombres y números) y se duermen si nadie se mueve,
// igual que el robot (10 s sin ver a nadie).
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const R = 62, OJOS = [{ cx: 150, cy: 112 }, { cx: 330, cy: 112 }];
  const DORMIR_TRAS = 10000;

  const EXPRESIONES = [
    null,
    { n: "Sorpresa", d: 1600, f: () => ({ sup: [1, 1], inf: [1, 1], pupila: .7, boca: { c: 0, a: 18, w: 26 } }) },
    { n: "Sueño", d: 3500, f: t => ({ sup: [.42 - .12 * Math.sin(t * 6), .42 - .12 * Math.sin(t * 6)], inf: [.8, .8], mira: { x: 0, y: .25 }, boca: { c: 2, a: 4, w: 22 }, sinParpadeo: true }) },
    { n: "Enojo", d: 2600, f: () => ({ sup: [.55, .55], inf: [.7, .7], incl: [16, 16], boca: { c: -10, a: 0, w: 50 } }) },
    { n: "Sospecha", d: 2800, f: t => ({ sup: [.4, .4], inf: [.5, .5], mira: { x: Math.sin(t * Math.PI * 2) * .7, y: 0 }, boca: { c: -3, a: 0, w: 34, dx: 14 } }) },
    { n: "Guiño", d: 1000, f: t => ({ sup: [1, t > .15 && t < .75 ? 0 : .85], inf: [.85, t > .15 && t < .75 ? 0 : .85], boca: { c: 16, a: 0, w: 60, dx: -6 }, sinParpadeo: true }) },
    { n: "Curioso", d: 2600, f: () => ({ sup: [1, .62], inf: [.95, .7], mira: { x: .25, y: -.25 }, boca: { c: 0, a: 8, w: 14 } }) },
    { n: "Feliz", d: 2600, f: () => ({ sup: [.85, .85], inf: [.45, .45], boca: { c: 26, a: 8, w: 84 } }) },
    { n: "Rodar los ojos", d: 1700, f: t => { const a = Math.PI * (1 - t); return { sup: [.9, .9], inf: [.9, .9], mira: { x: Math.cos(a) * .9, y: -Math.sin(a) * .9 }, boca: { c: -4, a: 0, w: 44 } }; } },
    { n: "Mirar alrededor", d: 3200, f: t => ({ mira: { x: t < .33 ? -1 : t < .66 ? 1 : 0, y: .05 }, boca: { c: 2, a: 0, w: 40 } }) },
    { n: "Pensar", d: 3200, f: () => ({ sup: [.82, .82], inf: [.62, .62], mira: { x: .7, y: -.85 }, boca: { c: -2, a: 0, w: 30, dx: 16 } }) },
    { n: "Triste", d: 3500, f: () => ({ sup: [.58, .58], inf: [.85, .85], incl: [-14, -14], mira: { x: 0, y: .45 }, boca: { c: -16, a: 0, w: 52 } }) },
    { n: "Parpadeo", d: 450, f: t => { const c = t < .45 ? 0 : (t - .45) / .55; return { sup: [c, c], inf: [c, c], sinParpadeo: true }; } },
    { n: "Confundido", d: 2600, f: () => ({ sup: [.48, 1], inf: [.7, 1], incl: [8, 0], mira: { x: -.2, y: -.2 }, boca: { c: 0, a: 0, w: 46, onda: 6 } }) },
    { n: "Nervioso", d: 2600, f: t => { const b = (t * 7) % 1 < .12 ? 0 : .95; return { sup: [b, b], inf: [b, b], mira: { x: Math.sin(t * 61) * .5, y: Math.cos(t * 47) * .3 }, boca: { c: -2, a: 0, w: 40, onda: 4 }, sinParpadeo: true }; } },
    { n: "Dormido", d: Infinity, f: t => ({ sup: [0, 0], inf: [0, 0], boca: { c: 0, a: 6 + 3 * Math.sin(t * 2.2), w: 14 }, zzz: true, sinParpadeo: true }) },
    { n: "Despierta", d: 2400, f: (t, ms) => {
        let s = ms < 900 ? .32 * ms / 900 : ms < 1050 ? .32 * (1 - (ms - 900) / 150) : ms < 1250 ? (ms - 1050) / 200 : 1;
        return { sup: [s, s], inf: [Math.min(1, s + .2), Math.min(1, s + .2)], boca: { c: 6, a: ms > 1200 ? 10 : 3, w: 30 }, sinParpadeo: true };
      } },
  ];
  const ESTADO_TXT = { 15: "Durmiendo · mueve el mouse", 16: "Despertando" };

  // ---------- Construcción del SVG ----------
  const instancias = [];
  let uid = 0;
  function el(tag, at, padre) { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); if (padre) padre.appendChild(e); return e; }

  function crear(svg) {
    const id = "o" + (uid++);
    svg.setAttribute("viewBox", "0 0 480 330");
    const defs = el("defs", {}, svg);
    const gi = el("radialGradient", { id: id + "iris", cx: "45%", cy: "40%", r: "60%" }, defs);
    el("stop", { offset: "0%", "stop-color": "#4fd36a" }, gi);
    el("stop", { offset: "70%", "stop-color": "#1a7a2e" }, gi);
    el("stop", { offset: "100%", "stop-color": "#0f4a1c" }, gi);
    const gl = el("linearGradient", { id: id + "lid", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: "0%", "stop-color": "#ff8a3d" }, gl);
    el("stop", { offset: "100%", "stop-color": "#e0570f" }, gl);
    const pat = el("pattern", { id: id + "pt", width: 9, height: 9, patternUnits: "userSpaceOnUse" }, defs);
    el("circle", { cx: 4.5, cy: 4.5, r: 1.3, fill: "rgba(0,0,0,.16)" }, pat);

    // Pantalla del notebook con la boca
    el("rect", { x: 40, y: 196, width: 400, height: 150, rx: 14, fill: "#0b0a07", stroke: "#3a382e", "stroke-width": 2 }, svg);
    el("circle", { cx: 240, cy: 206, r: 2.6, fill: "#2c2a21" }, svg);
    const boca = el("path", { fill: "#1a7a2e", stroke: "#2fae4a", "stroke-width": 5, "stroke-linecap": "round", "stroke-linejoin": "round" }, svg);
    const zzz = el("g", { "font-family": "Barlow Condensed, sans-serif", "font-weight": 700, fill: "#2fae4a", opacity: 0 }, svg);
    const zs = [0, 1, 2].map(i => { const t = el("text", { "font-size": 22 + i * 8 }, zzz); t.textContent = "z"; return t; });
    // Soporte central del mecanismo y barra
    el("rect", { x: 90, y: 176, width: 300, height: 14, rx: 5, fill: "#e0570f" }, svg);
    el("rect", { x: 90, y: 176, width: 300, height: 14, rx: 5, fill: `url(#${id}pt)` }, svg);
    el("rect", { x: 222, y: 70, width: 36, height: 110, rx: 7, fill: "#ff7a2a" }, svg);
    el("rect", { x: 229, y: 92, width: 22, height: 36, rx: 3, fill: "#2a4fb5" }, svg);   // servo azul
    el("circle", { cx: 240, cy: 84, r: 6, fill: "#fff", stroke: "#e0570f", "stroke-width": 3 }, svg);

    const ojos = OJOS.map(({ cx, cy }, i) => {
      const g = el("g", {}, svg);
      const cp = el("clipPath", { id: `${id}c${i}` }, defs);
      el("circle", { cx, cy, r: R + 4 }, cp);
      el("circle", { cx, cy, r: R + 6, fill: "#c4520f" }, g);
      el("circle", { cx, cy, r: R, fill: "#f4f2ea" }, g);
      const iris = el("g", {}, g);
      el("circle", { cx, cy, r: 25, fill: `url(#${id}iris)` }, iris);
      const pupila = el("circle", { cx, cy, r: 11, fill: "#0b0a07" }, iris);
      el("circle", { cx: cx - 8, cy: cy - 9, r: 5, fill: "#fff", opacity: .85 }, iris);
      const tapas = el("g", { "clip-path": `url(#${id}c${i})` }, g);
      const sup = el("path", { fill: `url(#${id}lid)`, stroke: "#b44a0c", "stroke-width": 3 }, tapas);
      const inf = el("path", { fill: `url(#${id}lid)`, stroke: "#b44a0c", "stroke-width": 3 }, tapas);
      el("circle", { cx, cy, r: R + 4, fill: "none", stroke: "#b44a0c", "stroke-width": 4 }, g);
      return { cx, cy, iris, pupila, sup, inf, interior: i === 0 ? 1 : -1 };
    });
    const inst = { svg, ojos, boca, zzz, zs, v: { sup: [.85, .85], inf: [.85, .85], incl: [0, 0], gx: 0, gy: 0, pupila: 1, boca: { c: 6, a: 0, w: 46, dx: 0, onda: 0 } } };
    instancias.push(inst);
    return inst;
  }

  // ---------- Estado compartido ----------
  let expr = 0, tExpr = 0, proxParpadeo = performance.now() + 2500, parpadeoHasta = 0;
  let mouse = null, ultimoMov = performance.now(), mirarAzar = { x: 0, y: 0 }, tAzar = 0;
  const avisos = [];
  function hacer(n) {
    if (expr === 15 && n !== 15) n = 16;          // de dormido siempre pasa por despertar
    expr = n; tExpr = performance.now();
    avisos.forEach(f => f(n));
  }

  window.Ojos = {
    crear, hacer, EXPRESIONES,
    alCambiar: f => avisos.push(f),
  };

  addEventListener("pointermove", e => {
    mouse = { x: e.clientX, y: e.clientY }; ultimoMov = performance.now();
    if (expr === 15) hacer(16);
  }, { passive: true });
  addEventListener("scroll", () => { ultimoMov = performance.now(); if (expr === 15) hacer(16); }, { passive: true });

  function mezclar(a, b, k) { return a + (b - a) * k; }

  function pathSup(cx, cy, s, incl, interior) {
    const y = cy - R + (1 - s) * R, yi = y + incl, yo = y - incl * .4;
    const [yl, yr] = interior > 0 ? [yo, yi] : [yi, yo];
    const curva = 16 * s;
    return `M${cx - R - 8},${cy - R - 12} L${cx + R + 8},${cy - R - 12} L${cx + R + 8},${yr} Q${cx},${(yl + yr) / 2 + curva} ${cx - R - 8},${yl} Z`;
  }
  function pathInf(cx, cy, s, incl, interior) {
    const y = cy + R - (1 - s) * R, yi = y - incl * .3;
    const [yl, yr] = interior > 0 ? [y, yi] : [yi, y];
    const curva = 12 * s;
    return `M${cx - R - 8},${cy + R + 12} L${cx + R + 8},${cy + R + 12} L${cx + R + 8},${yr} Q${cx},${(yl + yr) / 2 - curva} ${cx - R - 8},${yl} Z`;
  }
  function pathBoca(b) {
    const cx = 240 + (b.dx || 0), cy = 268, w = b.w / 2;
    if (b.onda) {
      let d = `M${cx - w},${cy}`;
      for (let i = 1; i <= 8; i++) d += ` L${cx - w + (2 * w * i) / 8},${cy + (i % 2 ? -b.onda : b.onda)}`;
      return { d, lleno: false };
    }
    const sup = `M${cx - w},${cy} Q${cx},${cy + b.c} ${cx + w},${cy}`;
    if (b.a < 1.5) return { d: sup, lleno: false };
    return { d: `${sup} Q${cx},${cy + b.c + b.a * 2.2} ${cx - w},${cy} Z`, lleno: true };
  }

  function cuadro(ahora) {
    // Expresión en curso
    let o = {};
    if (expr) {
      const E = EXPRESIONES[expr], ms = ahora - tExpr;
      if (ms > E.d) { expr = 0; avisos.forEach(f => f(0)); }
      else o = E.f(ms / (isFinite(E.d) ? E.d : 1000), ms) || {};
    }
    // Se duerme si nadie se mueve
    if (!expr && ahora - ultimoMov > DORMIR_TRAS) hacer(15);
    // Parpadeo sincronizado (los dos ojos a la vez)
    if (!o.sinParpadeo && ahora > proxParpadeo) { parpadeoHasta = ahora + 230; proxParpadeo = ahora + 2200 + Math.random() * 3800; }
    const parpadeando = !o.sinParpadeo && ahora < parpadeoHasta;
    // Mirada: la expresión manda; si no, el cursor; si no hay cursor, al azar
    if (ahora > tAzar) { mirarAzar = { x: Math.random() * 1.6 - .8, y: Math.random() * .8 - .4 }; tAzar = ahora + 1200 + Math.random() * 2000; }
    const quieto = ahora - ultimoMov > 3500;

    for (const inst of instancias) {
      const v = inst.v, r = inst.svg.getBoundingClientRect();
      if (r.bottom < -50 || r.top > innerHeight + 50) continue;
      let mira = o.mira;
      if (!mira) {
        if (mouse && !quieto) {
          const ex = r.left + r.width * .5, ey = r.top + r.height * (112 / 330);
          mira = { x: Math.max(-1, Math.min(1, (mouse.x - ex) / (r.width * .9))), y: Math.max(-1, Math.min(1, (mouse.y - ey) / (r.height * 1.1))) };
        } else mira = mirarAzar;
      }
      const k = .22;
      v.gx = mezclar(v.gx, mira.x, k); v.gy = mezclar(v.gy, mira.y, k);
      // Los párpados acompañan la mirada (como en el Arduino): mirar abajo baja el superior
      const base = { sup: [.85, .85], inf: [.85, .85] };
      for (let i = 0; i < 2; i++) {
        let s = (o.sup || base.sup)[i], n = (o.inf || base.inf)[i];
        if (!o.sup) { s -= Math.max(0, v.gy) * .3; n -= Math.max(0, -v.gy) * .3; }
        if (parpadeando) s = n = 0;
        v.sup[i] = mezclar(v.sup[i], s, parpadeando ? .55 : .25);
        v.inf[i] = mezclar(v.inf[i], n, parpadeando ? .55 : .25);
        v.incl[i] = mezclar(v.incl[i], (o.incl || [0, 0])[i], .2);
      }
      v.pupila = mezclar(v.pupila, o.pupila || 1, .2);
      const bo = o.boca || { c: 6, a: 0, w: 46 };
      for (const kk of ["c", "a", "w"]) v.boca[kk] = mezclar(v.boca[kk], bo[kk], .25);
      v.boca.dx = mezclar(v.boca.dx, bo.dx || 0, .25);
      v.boca.onda = bo.onda || 0;

      inst.ojos.forEach((ojo, i) => {
        ojo.iris.setAttribute("transform", `translate(${v.gx * 24},${v.gy * 20})`);
        ojo.pupila.setAttribute("r", 11 * v.pupila);
        ojo.sup.setAttribute("d", pathSup(ojo.cx, ojo.cy, v.sup[i], v.incl[i], ojo.interior));
        ojo.inf.setAttribute("d", pathInf(ojo.cx, ojo.cy, v.inf[i], v.incl[i], ojo.interior));
      });
      const b = pathBoca(v.boca);
      inst.boca.setAttribute("d", b.d);
      inst.boca.setAttribute("fill", b.lleno ? "#1a7a2e" : "none");
      // Zzz
      inst.zzz.setAttribute("opacity", o.zzz ? 1 : 0);
      if (o.zzz) inst.zs.forEach((z, i) => {
        const f = ((ahora / 2600) + i / 3) % 1;
        z.setAttribute("x", 300 + i * 22 + f * 40); z.setAttribute("y", 300 - f * 70 - i * 6);
        z.setAttribute("opacity", Math.sin(f * Math.PI).toFixed(2));
      });
    }
    requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
  window.Ojos.texto = n => n ? (ESTADO_TXT[n] || EXPRESIONES[n].n) : "Mirándote";
})();
