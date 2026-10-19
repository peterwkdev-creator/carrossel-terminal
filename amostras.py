"""Gera o mesmo post em vários temas e formatos, confere cada um e monta as
imagens de comparação, para escolher o padrão visual.

Uso: python amostras.py <pasta-do-post>

Saída em <post>/amostras/ (refeita a cada rodada; fora do git):
  <variante>/texto.md, html/, png/   o post com "tema:" e "formato:" no topo
  comparativo.png                    uma linha por variante, até 4 slides
  grade-perfil.png                   as capas como a grade do perfil recorta
"""
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

AQUI = pathlib.Path(__file__).resolve().parent
VARIANTES = [  # (pasta, rótulo, cabeçalho extra)
    ("terminal-4x5", "terminal · 4:5 (atual)", ""),
    ("minimo-4x5", "mínimo · 4:5", "tema: minimo\n"),
    ("janela-4x5", "janela · 4:5", "tema: janela\n"),
    ("terminal-3x4", "terminal · 3:4", "formato: 3:4\n"),
]
ESCALA = 0.3
FONTES = ("C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/Helvetica.ttc",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FUNDO, TEXTO, SUAVE = (24, 28, 34), (232, 238, 244), (169, 180, 191)


def fonte(tamanho):
    """A primeira fonte do sistema que existir; a padrão do Pillow se nenhuma."""
    for f in FONTES:
        if pathlib.Path(f).is_file():
            return ImageFont.truetype(f, tamanho)
    return ImageFont.load_default(tamanho)


def escolher_slides(total, quantos=4):
    """Até `quantos` slides espalhados pelo post, sempre com o primeiro e o último."""
    if total <= quantos:
        return list(range(1, total + 1))
    return sorted({round(1 + i * (total - 1) / (quantos - 1)) for i in range(quantos)})


def rodar(script, pasta):
    r = subprocess.run([sys.executable, str(AQUI / script), str(pasta)],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()


def recorte_3x4(im):
    """A grade do perfil mostra a capa em 3:4, cortando as laterais do 4:5."""
    w, h = im.size
    nova = round(h * 3 / 4)
    if nova >= w:
        return im
    x = (w - nova) // 2
    return im.crop((x, 0, x + nova, h))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    post = pathlib.Path(sys.argv[1]).resolve()
    base = post / "amostras"
    original = (post / "texto.md").read_text(encoding="utf-8")
    resultado = {}
    for pasta, rotulo, extra in VARIANTES:
        d = base / pasta
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        if (post / "capturas").is_dir():
            shutil.copytree(post / "capturas", d / "capturas")
        (d / "texto.md").write_text(extra + original, encoding="utf-8")
        cod, saida = rodar("gerar.py", d)
        if cod:
            sys.exit(f"ERRO ao gerar {pasta}: {saida[-1:]}")
        cod, saida = rodar("conferir.py", d)
        resultado[pasta] = (cod, [l for l in saida if "DEFEITO" in l or l.startswith("  ")][:12], saida[-1])
        print(f"{rotulo}: {saida[-1]}")
        if cod:
            for l in saida:
                if l.startswith("  ") and ":" in l:
                    print("   ", l.strip())

    SLIDES = escolher_slides(len(list((base / VARIANTES[0][0] / "png").glob("slide-*.png"))))
    f_rot = fonte(34)
    f_peq = fonte(24)
    gap, mx, topo = 24, 40, 64
    larg = round(1080 * ESCALA)
    alturas = [round((1440 if "3x4" in p else 1350) * ESCALA) for p, _, _ in VARIANTES]
    W = mx * 2 + len(SLIDES) * larg + (len(SLIDES) - 1) * gap
    H = sum(topo + a + gap for a in alturas) + mx
    comp = Image.new("RGB", (W, H), FUNDO)
    dr = ImageDraw.Draw(comp)
    y = mx // 2
    for (pasta, rotulo, _), alt in zip(VARIANTES, alturas):
        cod, _, ultima = resultado[pasta]
        dr.text((mx, y + 8), rotulo, font=f_rot, fill=TEXTO)
        dr.text((mx + 520, y + 18), ("conferido: " + ultima.split(" ")[0]).lower(), font=f_peq,
                fill=(86, 211, 100) if cod == 0 else (227, 179, 65))
        y += topo
        for i, n in enumerate(SLIDES):
            with Image.open(base / pasta / "png" / f"slide-{n:02d}.png") as im:
                comp.paste(im.resize((larg, alt), Image.LANCZOS), (mx + i * (larg + gap), y))
        y += alt + gap
    comp.save(base / "comparativo.png")

    # grade do perfil: capas recortadas em 3:4, lado a lado
    lw, lh = 300, 400
    G = Image.new("RGB", (mx * 2 + 4 * lw + 3 * 6, 130 + lh + 90), FUNDO)
    dg = ImageDraw.Draw(G)
    dg.text((mx, 30), "Grade do perfil: a capa de cada variante recortada em 3:4", font=f_rot, fill=TEXTO)
    dg.text((mx, 76), "simulação; o recorte 3:4 da grade é aproximado, não regra oficial",
            font=f_peq, fill=SUAVE)
    for i, (pasta, rotulo, _) in enumerate(VARIANTES):
        with Image.open(base / pasta / "png" / "slide-01.png") as im:
            G.paste(recorte_3x4(im).resize((lw, lh), Image.LANCZOS), (mx + i * (lw + 6), 130))
        dg.text((mx + i * (lw + 6), 130 + lh + 20), rotulo, font=f_peq, fill=SUAVE)
    G.save(base / "grade-perfil.png")
    print(f"comparativo {comp.size} e grade {G.size}: {base}")
    if any(c for c, _, _ in resultado.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
