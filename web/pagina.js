// Arma las partes interactivas de la página: los dos juegos de ojos, las fichas de expresiones,
// las barras de la nota cara + ropa y la animación al hacer scroll.
(() => {
  const O = window.Ojos;
  O.crear(document.getElementById("ojos-portada"));
  O.crear(document.getElementById("ojos-expresiones"));

  const DESCRIPCION = {
    1: "Ojos muy abiertos y pupila chica", 2: "Párpados pesados que caen", 3: "Párpados bajos, inclinados al centro",
    4: "Ojos entrecerrados que van de lado a lado", 5: "Cierra un solo ojo (la única asimetría)", 6: "Un ojo más abierto que el otro",
    7: "Los párpados de abajo suben, como mejillas", 8: "La mirada da la vuelta por arriba", 9: "Busca a la izquierda y a la derecha",
    10: "Mira arriba al costado mientras piensa", 11: "Párpados caídos hacia afuera, mirada baja", 12: "Un parpadeo, los dos ojos juntos",
    13: "Un ojo entrecerrado y el otro abierto", 14: "Mirada inquieta y parpadeos rápidos", 15: "Ojos cerrados y zzz: nadie a la vista",
    16: "Entreabre, parpadea y abre mirándote",
  };
  const RAPIDAS = [7, 1, 4, 5, 10, 11, 15];

  // Fichas de la portada
  const fichas = document.getElementById("fichas-portada");
  RAPIDAS.forEach(n => {
    const b = document.createElement("button");
    b.className = "ficha"; b.dataset.n = n;
    b.textContent = n === 15 ? "Dormir" : O.EXPRESIONES[n].n;
    b.onclick = () => O.hacer(n);
    fichas.appendChild(b);
  });

  // Lista de las 16 expresiones
  const lista = document.getElementById("lista-expresiones");
  for (let n = 1; n < O.EXPRESIONES.length; n++) {
    const b = document.createElement("button");
    b.className = "expresion"; b.dataset.n = n;
    b.innerHTML = `<span class="n">${String(n).padStart(2, "0")}</span><div><b>${O.EXPRESIONES[n].n}</b><span>${DESCRIPCION[n]}</span></div>`;
    b.onclick = () => O.hacer(n);
    lista.appendChild(b);
  }

  O.alCambiar(n => {
    document.querySelectorAll("[data-n]").forEach(e => e.classList.toggle("activa", +e.dataset.n === n));
    document.getElementById("estado-portada").textContent = O.texto(n);
    document.getElementById("estado-expresiones").textContent = O.texto(n);
  });

  // Nota conjunta cara + ropa (mismos pesos y umbral que seguir.py)
  const casos = [
    ["Cara clara y su ropa", 1.0, 1.0],
    ["Cara dudosa y su ropa", .57, .9],
    ["Cara dudosa, ropa de otro", .43, 0],
    ["Lejos: solo la ropa", null, 1.0],
    ["Desconocido con su ropa", 0, 1.0],
  ];
  const nota = document.getElementById("nota");
  casos.forEach(([txt, c, r]) => {
    let total, partes;
    if (c === null) { total = r * .85; partes = [0, total]; }
    else { total = .7 * c + .3 * r; partes = [.7 * c, .3 * r]; }
    const ok = total >= .5;
    const fila = document.createElement("div");
    fila.className = "fila";
    fila.innerHTML = `<span>${txt}</span><div class="pista"><div class="cara" style="width:0"></div><div class="ropa" style="width:0"></div></div><span class="num ${ok ? "ok" : "no"}">${total.toFixed(2)}</span>`;
    fila.dataset.partes = partes.join(",");
    nota.appendChild(fila);
  });

  // Peso de las descargas
  document.querySelectorAll("[data-peso]").forEach(async e => {
    try {
      const r = await fetch(e.dataset.peso, { method: "HEAD" });
      const b = +r.headers.get("content-length");
      if (r.ok && b) e.textContent = `${e.textContent} · ${b > 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.ceil(b / 1024) + " KB"}`;
    } catch (_) { /* sin servidor: queda solo el tipo */ }
  });

  // Aparecer al hacer scroll (y llenar las barras de la nota)
  const io = new IntersectionObserver(es => es.forEach(en => {
    if (!en.isIntersecting) return;
    en.target.classList.add("visto");
    en.target.querySelectorAll?.(".fila").forEach((f, i) => {
      const [c, r] = f.dataset.partes.split(",").map(Number);
      setTimeout(() => { f.querySelector(".cara").style.width = c * 100 + "%"; f.querySelector(".ropa").style.width = r * 100 + "%"; }, 150 * i);
    });
    io.unobserve(en.target);
  }), { threshold: .15 });
  document.querySelectorAll(".aparece").forEach(e => io.observe(e));

  // Menú: marca la sección visible
  const enlaces = [...document.querySelectorAll(".menu a")];
  const io2 = new IntersectionObserver(es => es.forEach(en => {
    if (en.isIntersecting) enlaces.forEach(a => a.classList.toggle("activo", a.getAttribute("href") === "#" + en.target.id));
  }), { rootMargin: "-45% 0px -50% 0px" });
  document.querySelectorAll("section[id]").forEach(s => io2.observe(s));
})();
