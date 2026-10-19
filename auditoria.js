// Mede o slide renderizado e grava o resultado em #auditoria (lido pelo conferir.py
// via --dump-dom). Mede: tamanho da letra, contraste com o fundo efetivo, se o texto
// cabe na tela e se o conteúdo transborda. Não mede texto dentro de imagem.
(function () {
  function cor(s) {
    const m = s.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }
  function sobre(c, base) { // compõe c (com alfa) sobre base opaca
    const a = c[3];
    return [0, 1, 2].map(i => c[i] * a + base[i] * (1 - a)).concat(1);
  }
  // A .deco (grade e brilho) fica atrás do texto, fora da cadeia de ancestrais.
  // Quem chega até o body sem fundo opaco é medido também contra --deco-pior,
  // a cor mais clara que a .deco alcança; sem essa variável, não se mede.
  const temDeco = !!document.querySelector(".deco");
  const decoPior = cor(getComputedStyle(document.body).getPropertyValue("--deco-pior").trim() || "none");
  function fundo(el, trocaCorpo) {
    const camadas = [];
    let semMedida = false, chegouCorpo = false;
    for (let e = el; e; e = e.parentElement) {
      const st = getComputedStyle(e);
      if (st.backgroundImage !== "none") semMedida = true;
      let c = cor(st.backgroundColor);
      if (e === document.body || e === document.documentElement) {
        chegouCorpo = true;
        if (trocaCorpo) c = trocaCorpo;
      }
      if (c && c[3] > 0) { camadas.push(c); if (c[3] >= 1) break; }
    }
    let base = [255, 255, 255, 1];
    for (const c of camadas.reverse()) base = sobre(c, base);
    return { cor: base, semMedida, chegouCorpo };
  }
  function lum(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function contraste(a, b) {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  }
  function medir() {
    const itens = [];
    // Mede contra a área do slide (body fixo em 1080x1350), não contra a janela:
    // no --dump-dom a janela do Chrome sem tela sai menor que no --screenshot.
    const corpo = document.body.getBoundingClientRect();
    const W = corpo.width, H = corpo.height;
    document.querySelectorAll("body *").forEach(el => {
      if (el.id === "auditoria" || el.closest("script,style,#auditoria")) return;
      const proprio = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
      if (!proprio.length) return;
      const st = getComputedStyle(el);
      if (st.display === "none" || st.visibility === "hidden") return;
      const f = fundo(el);
      let c = sobre(cor(st.color), f.cor);
      let ctr = contraste(c, f.cor);
      if (temDeco && f.chegouCorpo) {
        if (!decoPior) f.semMedida = true;
        else {
          const g = fundo(el, decoPior);
          ctr = Math.min(ctr, contraste(sobre(cor(st.color), g.cor), g.cor));
        }
      }
      const r = document.createRange();
      r.selectNodeContents(el);
      const b = r.getBoundingClientRect();
      itens.push({
        tag: el.tagName.toLowerCase(),
        texto: proprio.map(n => n.textContent).join(" ").replace(/\s+/g, " ").trim(),
        px: parseFloat(st.fontSize),
        contraste: Math.round(ctr * 100) / 100,
        fundoSemMedida: f.semMedida,
        foraDaTela: b.left < -1 || b.top < -1 || b.right > W + 1 || b.bottom > H + 1,
      });
    });
    // Conteúdo centralizado transborda para cima e para baixo: o scrollHeight só vê
    // o de baixo, então compara também a caixa de cada filho com a da área.
    const cont = document.querySelector(".conteudo");
    let transborda = null;
    if (cont) {
      const a = cont.getBoundingClientRect();
      transborda = cont.scrollHeight > cont.clientHeight + 1 ||
        [...cont.children].some(f => { const b = f.getBoundingClientRect();
          return b.top < a.top - 1 || b.bottom > a.bottom + 1; });
    }
    document.getElementById("auditoria").textContent = JSON.stringify({
      largura: W, altura: H,
      transborda,
      imagens: document.querySelectorAll("img").length,
      // Escala de exibição de cada imagem (object-fit: contain): acima de 1 a
      // captura foi ampliada e sai borrada no PNG.
      imagensInfo: [...document.querySelectorAll("img")].map(im => {
        const b = im.getBoundingClientRect();
        const ok = im.complete && im.naturalWidth > 0;
        return { src: decodeURIComponent(im.src.split("/").pop()), carregou: ok,
          natural: ok ? [im.naturalWidth, im.naturalHeight] : null,
          escala: ok ? Math.round(Math.min(b.width / im.naturalWidth, b.height / im.naturalHeight) * 100) / 100 : null };
      }),
      capturasPendentes: document.querySelectorAll(".captura").length,
      textoCompleto: document.body.innerText,
      itens,
    });
  }
  // Espera as imagens (load) e as fontes antes de medir.
  const pronto = () => (document.fonts ? document.fonts.ready : Promise.resolve()).then(medir);
  if (document.readyState === "complete") pronto(); else window.addEventListener("load", pronto);
})();
