"""Reel narrado: slides do carrossel + voz sintética + legenda queimada + trilha.

Uso: python reel_narrado.py <pasta-do-post> [voz] [--tts <pasta-do-tts>]
     (rodar o gerar.py antes; precisa do ffmpeg e do TTS)

Entrada: <post>/narracao.txt, linhas "N | frase" (N = slide; linha com # é
comentário). A voz sai do narrar.py do TTS (repositório tts-ptbr, opcional),
que grava voz.wav e tempos.json com o tempo de cada frase; o slide troca
quando começa a 1ª frase dele. Na tela, por SELO_S segundos, o selo "feito
com IA" com a versão do TTS.

Onde fica o TTS, nesta ordem: --tts <pasta>, a variável CARROSSEL_TTS, e a
pasta sys-tts ao lado desta. O Python do TTS: a variável CARROSSEL_TTS_PYTHON,
o .venv-kokoro dentro da pasta do TTS, ou o Python que roda este script.

Legenda: blocos de até PALAVRAS palavras, caixa escura, base em
y = ALT - MARGEM_LEG, no vão entre o texto do card e a barra de progresso
dele, dentro da zona segura do Reel, sem cobrir o card; a palavra já falada
fica verde (karaokê \\k, tempo por caracteres).
Trilha: a do reel.py, DB_TRILHA abaixo e com ducking (sidechaincompress) sob a
voz. Saída: <post>/reel/<voz>/<NN>-narrado.mp4.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

from gerar import ler
from reel import ALT, FADE, FPS, LARG, renderizar, trilha

AQUI = pathlib.Path(__file__).resolve().parent
PALAVRAS = 4
MARGEM_LEG = 550      # px da base da legenda até o pé da tela (base em y=1370:
                      # abaixo do texto mais baixo de um card cheio, ~1245, e
                      # acima da barra de progresso do card, ~1440)
MARGEM_SELO = 400     # px do topo: o vão entre o selo do card e o título
CAUDA = 1.2         # s de imagem depois da última frase
SELO_S = 4.0
DB_TRILHA = -22       # trilha ~22 dB abaixo antes do ducking (plano: 18 a 22 LU)
VERDE = "&H0050B93F"  # #3fb950 do modelo.css, em BGR do ASS

ASS_CAB = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {LARG}
PlayResY: {ALT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Legenda,Segoe UI,66,{VERDE},&H00FFFFFF,&H30000000,&H00000000,-1,0,0,0,100,100,0,0,3,14,0,2,90,90,{MARGEM_LEG},1
Style: Selo,Segoe UI,38,&H00FFFFFF,&H00FFFFFF,&H30000000,&H00000000,-1,0,0,0,100,100,0,0,3,10,0,8,90,90,{MARGEM_SELO},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def hms(s):
    cs = round(s * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def blocos(texto):
    """Corta a frase em blocos de até PALAVRAS palavras, fechando na pontuação."""
    saida, atual = [], []
    for p in texto.split():
        atual.append(p)
        if len(atual) >= PALAVRAS or re.search(r"[.,:;?!]$", p):
            saida.append(atual)
            atual = []
    if atual:
        saida.append(atual)
    return saida


def legenda(tempos, versao):
    linhas = [ASS_CAB]
    selo = (r"Feito com IA · revisado por um dev\N"
            f"voz sintética: TTS próprio ({versao})")
    linhas.append(f"Dialogue: 1,{hms(0)},{hms(SELO_S)},Selo,,0,0,0,,{selo}")
    for f in tempos:
        partes = blocos(f["texto"])
        total = sum(len(" ".join(b)) for b in partes)
        t = f["inicio"]
        for b in partes:
            d = (f["fim"] - f["inicio"]) * len(" ".join(b)) / total
            ks = [max(1, round(d * 100 * len(p) / len("".join(b)))) for p in b]
            texto = " ".join(f"{{\\k{k}}}{p}" for k, p in zip(ks, b))
            linhas.append(f"Dialogue: 0,{hms(t)},{hms(t + d)},Legenda,,0,0,0,,{texto}")
            t += d
    return "\n".join(linhas) + "\n"


def duracoes(tempos, n):
    """Tempo de cada slide para que a troca termine quando a 1ª frase dele começa."""
    inicio = {}
    for f in tempos["frases"]:
        inicio.setdefault(f["slide"], f["inicio"])
    if sorted(inicio) != list(range(1, n + 1)):
        sys.exit(f"ERRO: a narração cobre os slides {sorted(inicio)}, o post tem {n}")
    ds = [max(inicio[2], FADE + 0.1)]
    for k in range(2, n):
        ds.append(inicio[k + 1] - inicio[k] + FADE)
    ds.append(tempos["duracao"] + CAUDA - (inicio[n] - FADE))
    return [round(d, 3) for d in ds]


def achar_tts(args):
    """Pasta do TTS (--tts, CARROSSEL_TTS ou ../sys-tts) e o Python que o roda."""
    if "--tts" in args:
        i = args.index("--tts")
        tts = pathlib.Path(args[i + 1])
        del args[i:i + 2]
    else:
        tts = pathlib.Path(os.environ.get("CARROSSEL_TTS") or AQUI.parent / "sys-tts")
    tts = tts.resolve()
    if not (tts / "narrar.py").is_file():
        sys.exit(f"ERRO: narrar.py não encontrado em {tts}; aponte o TTS com --tts <pasta> "
                 "ou a variável CARROSSEL_TTS")
    py = os.environ.get("CARROSSEL_TTS_PYTHON")
    if not py:
        venv = [tts / ".venv-kokoro" / "Scripts" / "python.exe", tts / ".venv-kokoro" / "bin" / "python"]
        py = next((str(v) for v in venv if v.is_file()), sys.executable)
    return tts, py


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    tts, py = achar_tts(args)
    post = pathlib.Path(args[0]).resolve()
    voz = args[1] if len(args) > 1 else "alex"
    _, slides = ler(post)
    pasta = post / "reel" / voz
    subprocess.run([py, "narrar.py", str(post / "narracao.txt"), str(pasta), voz],
                   cwd=tts, check=True, stdout=subprocess.DEVNULL)
    tempos = json.loads((pasta / "tempos.json").read_text(encoding="utf-8"))
    ds = duracoes(tempos, len(slides))
    pngs = renderizar(post, len(slides))
    (pasta / "legenda.ass").write_text(legenda(tempos["frases"], tempos["versao"]),
                                       encoding="utf-8")
    total, trocas = trilha(ds, pasta / "trilha.wav")
    saida = pasta / f"{post.name.split('-')[1]}-narrado.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, d in zip(pngs, ds):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d}", "-i", str(p)]
    n = len(pngs)
    cmd += ["-i", "voz.wav", "-i", "trilha.wav"]
    filtros, ant, acum = [], "[0:v]", 0.0
    for k in range(1, n):
        acum += ds[k - 1] - FADE
        filtros.append(f"{ant}[{k}:v]xfade=transition=fade:duration={FADE}"
                       f":offset={acum:.3f}[v{k}]")
        ant = f"[v{k}]"
    filtros += [
        f"{ant}format=yuv420p,ass=legenda.ass[v]",
        f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[voz][chave]",
        f"[{n + 1}:a]volume={DB_TRILHA}dB[fundo]",
        "[fundo][chave]sidechaincompress=threshold=0.02:ratio=4:attack=20:release=300[duck]",
        "[voz][duck]amix=inputs=2:normalize=0:duration=longest,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]",
    ]
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
            "-movflags", "+faststart", saida.name]
    r = subprocess.run(cmd, cwd=pasta, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"ERRO no ffmpeg: {r.stderr[-800:]}")
    print("duração por slide (s):", ds)
    print(f"total {total:.2f} s, voz {tempos['duracao']} s ({tempos['versao']}, {voz})"
          f" -> {saida}")


if __name__ == "__main__":
    main()
