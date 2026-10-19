"""Versão em Reel de um carrossel: html/slide-NN.html -> reel/<post>-reel.mp4 (1080x1920).
Uso: python reel.py <pasta-do-post>   (rodar o gerar.py antes; precisa do ffmpeg)

Por quê: o criador do instagram.com não põe música em carrossel (conferido em
18/10/2026); som feito aqui só sai em Reel. A trilha é toda sintetizada no
próprio script, sem direito autoral de terceiros.

Imagem: cada slide é o próprio HTML do carrossel, com a página esticada para 9:16, o
fundo de terminal (.deco) na tela inteira e o slide 4:5 a ALTO px do topo (fica acima
da faixa de legenda e botões do Reel). O "deslize →" do slide 1 some: Reel não desliza.
Tempo: cada slide fica o bastante para ler (palavras / LEITURA + tempo por captura).
Som: pad de acordes que troca a cada slide, arpejo em semicolcheias com eco, pulso e
chimbal discretos, sopro de ruído em cada transição. Normalizado a -16 LUFS.
"""
import pathlib
import re
import subprocess
import sys
import wave

import numpy as np

from gerar import chrome, ler

LARG, ALT = 1080, 1920
TOPO = 200            # px do topo até o slide 4:5 (1350 de altura: vai até 1550)
FPS = 30
FADE = 0.5            # s de transição entre slides
LEITURA = 3.0         # palavras por segundo
POR_CAPTURA = 2.0     # s a mais para olhar cada captura de tela
MIN_S, MAX_S = 4.0, 10.0
CAPA_S = 6.0
SR = 48000
BPM = 100

CSS_REEL = f"""<style>
html {{ width: {LARG}px; height: {ALT}px; }}
body {{ margin-top: {TOPO}px; }}
.deco {{ position: fixed; inset: 0; }}
.seta {{ visibility: hidden; }}
</style></head>"""

# Lá menor, fá, dó, sol (i-VI-III-VII), em Hz, repetidos na ordem dos slides
ACORDES = [(110.00, 130.81, 164.81), (87.31, 110.00, 130.81),
           (130.81, 164.81, 196.00), (98.00, 123.47, 146.83)]


def duracoes(slides):
    """Segundos de cada slide no Reel, pelo número de palavras e de capturas."""
    ds = []
    for s in slides:
        texto = [ln for ln in s["linhas"] if ln.strip() and not ln.startswith(">")]
        capturas = sum(1 for ln in texto if ln.startswith(("[imagem", "[captura")))
        palavras = sum(len(re.findall(r"\w+", ln)) for ln in texto
                       if not ln.startswith(("[imagem", "[captura")))
        d = palavras / LEITURA + capturas * POR_CAPTURA
        if s["tipo"] == "capa":
            d = min(d, CAPA_S)        # gancho: a capa não segura 10 s
        elif s["tipo"] == "fontes":
            d = MIN_S                 # link não se lê em Reel: quem quiser pausa
        ds.append(round(min(MAX_S, max(MIN_S, d)), 2))
    return ds


def renderizar(post, n):
    """Fotografa cada slide em 9:16 (reel/png/slide-NN.png) e devolve os caminhos."""
    pasta = post / "reel" / "png"
    pasta.mkdir(parents=True, exist_ok=True)
    (post / "reel" / "html").mkdir(exist_ok=True)
    pngs = []
    for i in range(1, n + 1):
        h = (post / "html" / f"slide-{i:02d}.html").read_text(encoding="utf-8")
        if "</head>" not in h:
            sys.exit(f"ERRO: slide-{i:02d}.html sem </head>")
        dest = post / "reel" / "html" / f"slide-{i:02d}.html"
        dest.write_text(h.replace("</head>", CSS_REEL, 1), encoding="utf-8")
        p = pasta / f"slide-{i:02d}.png"
        p.unlink(missing_ok=True)
        chrome(f"--screenshot={p}", dest.as_uri(), largura=LARG, altura=ALT)
        from PIL import Image
        with Image.open(p) as im:
            if im.size != (LARG, ALT):
                sys.exit(f"ERRO: {p.name} saiu {im.size}, esperado {(LARG, ALT)}")
        pngs.append(p)
    return pngs


def env_exp(n, taxa):
    return np.exp(-taxa * np.arange(n) / SR)


def trilha(ds, wav):
    """Sintetiza a trilha estéreo para as durações ds; devolve (total, entradas)."""
    total = sum(ds) - FADE * (len(ds) - 1)
    N = int(total * SR)
    t = np.arange(N) / SR
    rng = np.random.default_rng(18)
    trocas = [0.0]
    for d in ds[:-1]:
        trocas.append(trocas[-1] + d - FADE)
    meios = [x + FADE / 2 for x in trocas[1:]]      # troca de acorde no meio da transição
    limites = [0.0] + meios + [total]

    # pad: dente de serra com 6 harmônicos, 3 vozes levemente desafinadas
    pad = np.zeros(N)
    for k in range(len(ds)):
        a, b = limites[k], limites[k + 1]
        i0, i1 = max(0, int((a - FADE) * SR)), min(N, int((b + FADE) * SR))
        tt = t[i0:i1]
        seg = np.zeros(i1 - i0)
        for f in ACORDES[k % len(ACORDES)]:
            for dt in (-0.003, 0.0, 0.003):
                for h in range(1, 7):
                    seg += np.sin(2 * np.pi * f * (1 + dt) * h * tt + h * dt * 50) / h
        env = np.clip(np.minimum((tt - (a - FADE)) / FADE, ((b + FADE) - tt) / FADE), 0, 1)
        pad[i0:i1] += seg * env
    pad *= 0.5 + 0.15 * np.sin(2 * np.pi * 0.11 * t)
    pad /= np.abs(pad).max()

    # arpejo em semicolcheias, uma oitava acima, com eco
    semi = 60 / BPM / 4
    arp = np.zeros(N)
    nota = int(semi * SR * 2.5)
    ordem = (0, 1, 2, 1, 0, 2, 1, 2)
    for j in range(int(total / semi)):
        t0 = j * semi
        k = max(i for i, x in enumerate(limites[:-1]) if x <= t0)
        f = ACORDES[k % len(ACORDES)][ordem[j % len(ordem)]] * 4
        i0 = int(t0 * SR)
        m = min(nota, N - i0)
        tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env_exp(m, 9)
        arp[i0:i0 + m] += s * (1.0 if j % 4 == 0 else 0.6)
    atraso = int(3 * semi * SR)
    eco = np.zeros(N)
    eco[atraso:] = arp[:-atraso] * 0.35
    eco[2 * atraso:] += arp[:-2 * atraso] * 0.12

    # pulso grave (tempos 1 e 3) e chimbal nas colcheias
    batida = 60 / BPM
    pulso = np.zeros(N)
    chimbal = np.zeros(N)
    for j in range(int(total / batida * 2)):
        i0 = int(j * batida / 2 * SR)
        if j % 4 == 0:
            m = min(int(0.35 * SR), N - i0)
            tt = np.arange(m) / SR
            freq = 45 + 45 * np.exp(-tt * 25)
            pulso[i0:i0 + m] += np.sin(2 * np.pi * np.cumsum(freq) / SR) * env_exp(m, 10)
        m = min(int(0.06 * SR), N - i0)
        ruido = np.diff(rng.standard_normal(m + 1))
        chimbal[i0:i0 + m] += ruido * env_exp(m, 70) * (0.8 if j % 2 else 0.4)

    # sopro de ruído filtrado em cada transição
    sopro = np.zeros(N)
    for x in trocas[1:]:
        i0 = int((x - 0.4) * SR)
        m = int((0.4 + FADE + 0.3) * SR)
        r = np.convolve(rng.standard_normal(m), np.ones(40) / 40, mode="same")
        tt = np.arange(m) / SR
        env = np.where(tt < 0.4 + FADE / 2, tt / (0.4 + FADE / 2), np.exp(-(tt - 0.4 - FADE / 2) * 6))
        sopro[i0:i0 + m] += r * env

    def norm(x):
        return x / (np.abs(x).max() or 1)

    base = 0.55 * pad + 0.22 * norm(pulso) + 0.05 * norm(chimbal) + 0.08 * norm(sopro)
    esq = base + 0.16 * norm(arp) + 0.10 * norm(eco)
    dir_ = base + 0.13 * norm(arp) + 0.14 * np.roll(norm(eco), int(0.012 * SR))
    est = np.stack([esq, dir_], axis=1)
    fade_in, fade_out = int(1.0 * SR), int(2.0 * SR)
    est[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    est[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    est = est / np.abs(est).max() * 0.8
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((est * 32767).astype("<i2").tobytes())
    return total, trocas


def montar(pngs, ds, wav, saida):
    """Junta as imagens com transição e a trilha num MP4 (ffmpeg)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, d in zip(pngs, ds):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d}", "-i", str(p)]
    cmd += ["-i", str(wav)]
    filtros, ant, acum = [], "[0:v]", 0.0
    for k in range(1, len(pngs)):
        acum += ds[k - 1] - FADE
        rot = f"[v{k}]"
        filtros.append(f"{ant}[{k}:v]xfade=transition=fade:duration={FADE}:offset={acum:.3f}{rot}")
        ant = rot
    filtros.append(f"{ant}format=yuv420p[v]")
    filtros.append(f"[{len(pngs)}:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]")
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
            "-movflags", "+faststart", str(saida)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"ERRO no ffmpeg: {r.stderr[-800:]}")


def main():
    post = pathlib.Path(sys.argv[1]).resolve()
    cab, slides = ler(post)
    if cab.get("formato", "4:5") != "4:5":
        sys.exit("ERRO: o Reel assume slide 4:5 (1080x1350)")
    ds = duracoes(slides)
    pngs = renderizar(post, len(slides))
    wav = post / "reel" / "trilha.wav"
    total, trocas = trilha(ds, wav)
    saida = post / "reel" / f"{post.name.split('-')[0]}-{post.name.split('-')[1]}-reel.mp4"
    montar(pngs, ds, wav, saida)
    print("duração por slide (s):", ds)
    print("entrada de cada slide (s):", [round(x, 2) for x in trocas])
    print(f"total {total:.2f} s -> {saida}")


if __name__ == "__main__":
    main()
