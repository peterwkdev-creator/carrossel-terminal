# Exemplos

`post-exemplo/` é um post curto e fictício (5 slides) com tudo o que um post
precisa: o `texto.md`, de onde saem os slides, e o `narracao.txt`, que só o
Reel narrado usa. Os comandos abaixo rodam da raiz do repositório.

## 1. Gerar os slides

```bash
python gerar.py exemplos/post-exemplo
```

Sai `5 slides em PNG 1080x1350` e as pastas `html/` e `png/` dentro do post.
Para só o HTML, sem abrir o navegador: `--sem-png`.

## 2. Conferir antes de publicar

```bash
python conferir.py exemplos/post-exemplo --publicar
```

O exemplo sai `APROVADO`. Para ver o conferidor reprovar, troque uma linha do
`texto.md` por `<p style="font-size:22px">letra pequena</p>`, gere de novo e
confira: sai `DEFEITO: slide-NN.html: letra 22px < 30` e a saída é 1.

Sem `--publicar`, pendência (captura marcada com `[captura: ...]`, campo
`PREENCHER`, link atrás de anti-robô) vira aviso e não reprova; com ele,
reprova.

## 3. Virar Reel

```bash
python reel.py exemplos/post-exemplo
```

Precisa do ffmpeg. Sai `exemplos/post-exemplo/reel/post-exemplo-reel.mp4`,
1080×1920, com cada slide no tempo de leitura dele e a trilha sintetizada.

## 4. Reel narrado (opcional)

Com o TTS [`tts-ptbr`](https://github.com/peterwkdev-creator/tts-ptbr) instalado
numa pasta qualquer:

```bash
python reel_narrado.py exemplos/post-exemplo alex --tts ../tts-ptbr
```

Cada linha do `narracao.txt` é `slide | frase`; o slide troca quando começa a
primeira frase dele. Sai em `exemplos/post-exemplo/reel/alex/`.

## 5. Comparar temas e formatos

```bash
python amostras.py exemplos/post-exemplo
```

Gera o post nos temas terminal, mínimo e janela e no formato 3:4, confere cada
um e monta `amostras/comparativo.png` e `amostras/grade-perfil.png`.

## Seu post

Copie `post-exemplo/` para uma pasta nova, reescreva o `texto.md` e rode os
mesmos comandos com o caminho dela.
