"""Gera os slides de um post: texto.md -> html/slide-NN.html -> png/slide-NN.png.

Uso: python gerar.py <pasta-do-post> [--sem-png]
     python gerar.py --versao

Formato do texto.md (o mesmo arquivo é o texto revisado slide a slide):
  selo: TESTADO 18/10 · Claude Code v2.1.299   (cabeçalho, antes do 1º slide)
  tema: minimo | janela   (opcional: temas/<tema>.css por cima do modelo.css)
  formato: 4:5 (1080x1350, padrão) | 3:4 (1080x1440)
  --- slide capa | --- slide | --- slide fontes
  # título            ## subtítulo         - item de lista
  | a | b |  tabela (1ª linha = cabeçalho)  [captura: o que capturar]
  [imagem: capturas/arquivo.png | rótulo da janela]   (caminho relativo ao post)
  // rótulo acima do título (// ! sai em âmbar)
  > nota de conferência (fonte, data): fica no .md, não vai para a imagem
  **destaque**  `código`  !!alerta!!  (em linha)
"""
import html
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

__version__ = "0.1.0"

# Onde procurar o navegador headless, nesta ordem: a variável CHROME, os nomes
# no PATH e os lugares de instalação mais comuns (Windows e macOS).
NOMES_CHROME = ("chrome", "google-chrome", "google-chrome-stable", "chromium",
                "chromium-browser", "msedge", "microsoft-edge")
LUGARES_CHROME = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
LARGURA, ALTURA = 1080, 1350
FORMATOS = {"4:5": (1080, 1350), "3:4": (1080, 1440)}
AQUI = pathlib.Path(__file__).resolve().parent


def em_linha(texto):
    """Marcação em linha do texto.md (**destaque**, `código`, !!alerta!!) em HTML."""
    t = html.escape(texto, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r'<b class="dest">\1</b>', t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"!!(.+?)!!", r'<b class="alerta">\1</b>', t)
    return t


def ler(post):
    """Lê <post>/texto.md e devolve (cabeçalho, slides); cada slide é {tipo, linhas}."""
    linhas = (post / "texto.md").read_text(encoding="utf-8").splitlines()
    cab, slides, atual = {}, [], None
    for ln in linhas:
        if ln.startswith("--- slide"):
            atual = {"tipo": ln[len("--- slide"):].strip() or "texto", "linhas": []}
            slides.append(atual)
        elif atual is None:
            m = re.match(r"(\w+):\s*(.+)", ln)
            if m:
                cab[m.group(1)] = m.group(2).strip()
        else:
            atual["linhas"].append(ln)
    return cab, slides


def corpo(linhas, post):
    """HTML do miolo de um slide, a partir das linhas dele no texto.md."""
    partes, tabela, lista = [], [], []

    def fecha():
        if lista:
            partes.append("<ul>" + "".join(f"<li>{em_linha(x)}</li>" for x in lista) + "</ul>")
            lista.clear()
        if tabela:
            cab, *resto = tabela
            h = "".join(f"<th>{em_linha(c)}</th>" for c in cab)
            r = "".join("<tr>" + "".join(f"<td>{em_linha(c)}</td>" for c in l) + "</tr>" for l in resto)
            partes.append(f"<table><tr>{h}</tr>{r}</table>")
            tabela.clear()

    for ln in linhas:
        s = ln.strip()
        if s.startswith("|") and set(s) <= set("|-: "):
            continue  # linha separadora de tabela markdown
        if s.startswith("|"):
            if lista:
                fecha()
            tabela.append([c.strip() for c in s.strip("|").split("|")])
            continue
        if s.startswith("- "):
            if tabela:
                fecha()
            lista.append(s[2:])
            continue
        fecha()
        if not s or s.startswith(">"):
            continue
        if s.startswith("## "):
            partes.append(f"<h2>{em_linha(s[3:])}</h2>")
        elif s.startswith("# "):
            partes.append(f"<h1>{em_linha(s[2:])}</h1>")
        elif s.startswith("// "):
            classe = "kicker alerta-k" if s.startswith("// !") else "kicker"
            partes.append(f'<div class="{classe}">{em_linha(s)}</div>')
        elif m := re.match(r"\[imagem:\s*([^|\]]+?)\s*(?:\|\s*(.+))?\]$", s):
            arq = (post / m.group(1)).resolve()
            if not arq.is_file():
                sys.exit(f"ERRO: imagem não encontrada: {arq}")
            rotulo = em_linha(m.group(2) or arq.name)
            partes.append(
                '<figure class="tela"><div class="barra"><i></i><i></i><i></i>'
                f'<span class="rotulo-ok">{rotulo}</span></div>'
                f'<div class="quadro"><img src="{arq.as_uri()}" alt=""></div></figure>'
            )
        elif m := re.match(r"\[captura:\s*(.+)\]$", s):
            partes.append(
                '<div class="captura"><div class="barra"><i></i><i></i><i></i>'
                '<span class="rotulo">CAPTURA PENDENTE</span></div>'
                f'<div class="descr"><span>{em_linha(m.group(1))}</span></div></div>'
            )
        elif s.startswith("<"):
            partes.append(s)  # HTML cru (usado nas provas do conferidor)
        else:
            partes.append(f"<p>{em_linha(s)}</p>")
    fecha()
    return "\n".join(partes)


def dimensoes(cab):
    """(largura, altura) do formato pedido no cabeçalho; 4:5 se não houver."""
    f = cab.get("formato", "4:5")
    if f not in FORMATOS:
        sys.exit(f"ERRO: formato {f!r} desconhecido; use {', '.join(FORMATOS)}")
    return FORMATOS[f]


def pagina(cab, slide, n, total, post):
    """Página HTML completa do slide n de total, com o CSS e a auditoria embutidos."""
    css = (AQUI / "modelo.css").read_text(encoding="utf-8")
    tema = cab.get("tema", "")
    if tema:
        css += "\n" + (AQUI / "temas" / f"{tema}.css").read_text(encoding="utf-8")
    larg, alt = dimensoes(cab)
    css += f"\nhtml, body {{ width: {larg}px; height: {alt}px; }}\n"
    js = (AQUI / "auditoria.js").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<style>{css}</style></head>
<body class="tipo-{slide['tipo']}{' tema-' + tema if tema else ''}">
<div class="deco" aria-hidden="true"></div>
<header><span class="selo">{em_linha(cab.get('selo', 'TESTADO ?? · Claude Code v?'))}</span>
<span class="contador"><b>{n:02d}</b>/{total:02d}</span></header>
<main class="conteudo">
{corpo(slide['linhas'], post)}
</main>
<footer><div class="progresso" aria-hidden="true">{''.join('<i class="feito"></i>' if i <= n else '<i></i>' for i in range(1, total + 1))}</div>
<div class="assina"><span>{em_linha(cab.get('rodape', '@peterwk.dev'))}</span>{'<span class="seta">deslize →</span>' if n == 1 < total else ''}</div></footer>
<pre id="auditoria" hidden></pre>
<script>{js}</script>
</body></html>"""


def achar_chrome():
    """Caminho do Chrome, Chromium ou Edge; None se nenhum for achado."""
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for nome in NOMES_CHROME:
        if achado := shutil.which(nome):
            return achado
    for lugar in LUGARES_CHROME:
        if pathlib.Path(lugar).is_file():
            return lugar
    return None


def chrome(*args, largura=LARGURA, altura=ALTURA):
    """Roda o navegador headless numa janela de largura x altura e devolve o processo."""
    exe = achar_chrome()
    if not exe:
        sys.exit("ERRO: Chrome/Chromium não encontrado; instale um ou aponte a variável CHROME")
    perfil = pathlib.Path(tempfile.gettempdir()) / "carrossel-chrome-headless"
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", f"--window-size={largura},{altura}",
           f"--user-data-dir={perfil}", "--no-first-run", *args]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=90)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    if sys.argv[1] == "--versao":
        print(__version__)
        return
    post = pathlib.Path(sys.argv[1]).resolve()
    cab, slides = ler(post)
    larg, alt = dimensoes(cab)
    (post / "html").mkdir(exist_ok=True)
    for f in (post / "html").glob("slide-*.html"):
        f.unlink()
    for i, s in enumerate(slides, 1):
        (post / "html" / f"slide-{i:02d}.html").write_text(pagina(cab, s, i, len(slides), post), encoding="utf-8")
    if "--sem-png" in sys.argv:
        print(f"{len(slides)} slides em HTML (sem PNG)")
        return
    (post / "png").mkdir(exist_ok=True)
    for f in (post / "png").glob("slide-*.png"):
        f.unlink()
    from PIL import Image
    for i in range(1, len(slides) + 1):
        h = post / "html" / f"slide-{i:02d}.html"
        p = post / "png" / f"slide-{i:02d}.png"
        chrome(f"--screenshot={p}", h.as_uri(), largura=larg, altura=alt)
        with Image.open(p) as im:
            if im.size != (larg, alt):
                sys.exit(f"ERRO: {p.name} saiu {im.size}, esperado {(larg, alt)}")
    print(f"{len(slides)} slides em PNG {larg}x{alt}: {post / 'png'}")


if __name__ == "__main__":
    main()
