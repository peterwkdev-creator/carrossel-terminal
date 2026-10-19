# Segurança

## Como avisar

Falha de segurança não vai em issue pública: use o aviso privado do GitHub,
em [Security → Report a vulnerability](https://github.com/peterwkdev-creator/carrossel-terminal/security/advisories/new).
Diga a versão (`python gerar.py --versao`), o passo a passo para reproduzir e o efeito.

## O que esperar

- Primeira resposta em até 14 dias.
- A correção sai na última versão publicada; versões antigas não recebem
  correção.
- Crédito no [CHANGELOG.md](CHANGELOG.md) e no aviso, se você quiser.

## O que não é falha de segurança

Resultado diferente do esperado (um valor, uma regra, um caso que falta) é
issue comum, pelo modelo "Resultado diferente do esperado".

O que os scripts fazem, para quem avalia o risco: leem o `texto.md` do post,
gravam HTML, PNG, WAV e MP4 só dentro da pasta do post, abrem o Chrome sem
tela (com perfil próprio, na pasta temporária) em arquivo local, chamam o
ffmpeg e, no `conferir.py`, fazem GET em cada link escrito nos slides. Não
pedem credencial, não publicam nada e não mandam o post para fora.
