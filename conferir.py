"""Confere os slides HTML de um post antes de exportar/publicar.

Uso: python conferir.py <pasta-do-post> [--publicar]   (rodar o gerar.py antes)

Barra (saída 1): letra abaixo de MIN_PX, contraste abaixo de CONTRASTE_MIN,
texto fora da tela ou transbordando, link escrito na imagem que não dá 200.
Avisa (com --publicar, barra): captura pendente.
Não mede: texto dentro de imagem (captura real) e fundo com imagem/gradiente;
diz quantos ficaram de fora.
"""
import html
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gerar import chrome, dimensoes, ler  # noqa: E402

MIN_PX = 30          # 1080 px de largura: 30 px ~ 11 px no celular
CONTRASTE_MIN = 4.5  # WCAG AA, texto normal
MAX_AMPLIA = 1.1     # captura exibida acima de 110% do tamanho real sai borrada
LINK = re.compile(
    r"(?<![\w@.\-/])(?:https?://)?(?:[a-z0-9-]+\.)+(?:com|dev|ai|io|org|net|br|app)\b(?:/[\w\-./%#?=&]*)?",
    re.I,
)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
_cache = {}


def status(url):
    """Código HTTP do link (com cache por rodada), ou o motivo de não ter código."""
    if not url.lower().startswith("http"):
        url = "https://" + url
    if url not in _cache:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                _cache[url] = r.status
        except urllib.error.HTTPError as e:
            # Desafio anti-robô do Cloudflare: o instrumento não vê a página.
            # Não é 200 nem 404: vira pendência a conferir no navegador.
            desafio = (e.headers.get("cf-mitigated") or "").lower() == "challenge"
            _cache[url] = "desafio anti-robô" if desafio else e.code
        except Exception as e:  # rede, DNS, TLS
            _cache[url] = f"erro: {type(e).__name__}"
    return _cache[url]


def auditar(arq):
    """Abre o slide no Chrome headless e lê o JSON que o auditoria.js grava no DOM."""
    r = chrome("--dump-dom", "--virtual-time-budget=5000", arq.as_uri())
    m = re.search(r'<pre id="auditoria"[^>]*>(.*?)</pre>', r.stdout, re.S)
    if not m or not m.group(1).strip():
        return None
    return json.loads(html.unescape(m.group(1)))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    post = pathlib.Path(sys.argv[1]).resolve()
    publicar = "--publicar" in sys.argv
    arqs = sorted((post / "html").glob("slide-*.html"))
    if not arqs:
        sys.exit(f"ERRO: nenhum slide em {post / 'html'} (rode o gerar.py)")
    larg, alt = dimensoes(ler(post)[0])
    defeitos, avisos, medidos, fora_img, fora_fundo, links = [], [], 0, 0, 0, set()
    for a in arqs:
        d = auditar(a)
        if d is None or not d["itens"]:
            defeitos.append(f"{a.name}: auditoria não rodou ou não achou texto (instrumento cego)")
            continue
        if (d["largura"], d["altura"]) != (larg, alt):
            defeitos.append(f"{a.name}: janela {d['largura']}x{d['altura']}, esperado {larg}x{alt}")
        if d["transborda"]:
            defeitos.append(f"{a.name}: conteúdo transborda a área do slide")
        for it in d["itens"]:
            medidos += 1
            t = it["texto"][:40]
            if it["px"] < MIN_PX:
                defeitos.append(f"{a.name}: letra {it['px']:g}px < {MIN_PX} em <{it['tag']}> \"{t}\"")
            if it["fundoSemMedida"]:
                fora_fundo += 1
            elif it["contraste"] < CONTRASTE_MIN:
                defeitos.append(f"{a.name}: contraste {it['contraste']}:1 < {CONTRASTE_MIN} em <{it['tag']}> \"{t}\"")
            if it["foraDaTela"]:
                defeitos.append(f"{a.name}: texto fora da tela em <{it['tag']}> \"{t}\"")
        fora_img += d["imagens"]
        for im in d.get("imagensInfo", []):
            if not im["carregou"]:
                defeitos.append(f"{a.name}: imagem {im['src']} não carregou")
            elif im["escala"] > MAX_AMPLIA:
                w, h = im["natural"]
                defeitos.append(f"{a.name}: imagem {im['src']} ({w}x{h}) ampliada {im['escala']:g}x: sai borrada")
        if d["capturasPendentes"]:
            avisos.append(f"{a.name}: {d['capturasPendentes']} captura(s) pendente(s)")
        if "PREENCHER" in d["textoCompleto"]:
            avisos.append(f"{a.name}: campo PREENCHER em aberto")
        for u in LINK.findall(d["textoCompleto"]):
            u = u.rstrip(".,;:)")
            links.add(u)
            s = status(u)
            if s == "desafio anti-robô":
                avisos.append(f"{a.name}: link {u} atrás de desafio anti-robô: conferir no navegador")
            elif s != 200:
                defeitos.append(f"{a.name}: link {u} deu {s}, esperado 200")
    print(f"Conferidos: {len(arqs)} slides, {medidos} blocos de texto, {len(links)} links distintos")
    for u in sorted(links):
        print(f"  link {u}: {status(u)}")
    print(f"Fora da medida: {fora_img} imagem(ns) (texto em captura não se mede), "
          f"{fora_fundo} bloco(s) sobre fundo com imagem/gradiente (contraste não medido)")
    for x in avisos:
        print("AVISO:", x)
    for x in defeitos:
        print("DEFEITO:", x)
    if defeitos or (publicar and avisos):
        print(f"REPROVADO: {len(defeitos)} defeito(s)" + (f", {len(avisos)} pendência(s)" if publicar else ""))
        sys.exit(1)
    print("APROVADO" + ("" if publicar or not avisos else " (com pendências: não publicar ainda)"))


if __name__ == "__main__":
    main()
