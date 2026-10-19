"""As duas provas do conferidor: todo detector novo só entra com as duas.

Prova 1: pega o plantado. provas/plantado/ tem letra de 22 px, contraste baixo,
link morto e conteúdo que transborda; o conferidor tem de reprovar e citar os quatro.
Prova 2: zero falso positivo. Os exemplos/ deste repositório, todo post-*/ da
pasta de cima (se houver, já gerado) e o provas/limpo/ têm de sair sem DEFEITO
(avisos de pendência não contam).

Uso: python provas.py
"""
import pathlib
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
# trecho que tem de aparecer na saída do conferir.py -> defeito plantado
ESPERADOS = {"letra 22px": "letra pequena", "\"Cinza escuro": "contraste baixo",
             "\"Cinza médio": "contraste baixo só sobre a grade/brilho (--deco-pior)",
             "nao-existe-pkd-prova deu 404": "link morto", "transborda": "transbordo",
             "pequena.png (160x90) ampliada": "captura ampliada"}


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def capturas_de_prova(plantado, limpo):
    """Imagens das provas, refeitas a cada rodada (determinísticas)."""
    from PIL import Image, ImageDraw
    for pasta, nome, tam in ((plantado, "pequena.png", (160, 90)), (limpo, "nitida.png", (1400, 900))):
        (pasta / "capturas").mkdir(exist_ok=True)
        im = Image.new("RGB", tam, "#0d1117")
        d = ImageDraw.Draw(im)
        for y in range(10, tam[1], 30):
            d.text((12, y), "$ claude --version", fill="#3fb950")
        im.save(pasta / "capturas" / nome)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    falhas = []
    plantado = AQUI / "provas" / "plantado"
    limpo = AQUI / "provas" / "limpo"
    capturas_de_prova(plantado, limpo)
    rodar(AQUI / "gerar.py", plantado, "--sem-png")
    cod, saida = rodar(AQUI / "conferir.py", plantado)
    pegos = [nome for chave, nome in ESPERADOS.items() if chave in saida]
    print(f"Prova 1 (plantado): saída {cod}, pegou {len(pegos)}/{len(ESPERADOS)}: {', '.join(pegos)}")
    if cod != 1 or len(pegos) != len(ESPERADOS):
        falhas.append("prova 1: o conferidor deixou passar defeito plantado")
        print(saida)
    exemplos = sorted(p for p in (AQUI / "exemplos").glob("*") if (p / "texto.md").is_file())
    for p in exemplos:
        rodar(AQUI / "gerar.py", p, "--sem-png")
    posts = exemplos + sorted(p for p in RAIZ.glob("post-*") if (p / "html").is_dir())
    # O acervo pode não ter captura real: o "limpo" traz uma captura nítida que
    # exercita a checagem de imagem e tem de passar sem defeito.
    rodar(AQUI / "gerar.py", limpo, "--sem-png")
    posts.append(limpo)
    for p in posts:
        cod, saida = rodar(AQUI / "conferir.py", p)
        defeitos = [l for l in saida.splitlines() if l.startswith("DEFEITO")]
        print(f"Prova 2 ({p.name}): saída {cod}, {len(defeitos)} defeito(s)")
        if cod != 0 or defeitos:
            falhas.append(f"prova 2: {p.name} reprovado (falso positivo ou defeito real)")
            print(saida)
    print("PROVAS OK" if not falhas else "PROVAS FALHARAM:\n  " + "\n  ".join(falhas))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
