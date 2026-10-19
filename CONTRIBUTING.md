# Como contribuir

Resultado errado: abra uma issue pelo modelo "Resultado diferente do
esperado". Caso que falta, ideia ou dúvida: pelo modelo "Sugestão ou
dúvida". Para mandar código:

- Os testes rodam do checkout, depois do `pip install -r requirements.txt`
  (os do conferidor pedem Chrome ou Chromium e rede; sem navegador, são pulados):

  ```bash
  python -m unittest
  ```

- Dependências só as do `requirements.txt` (Pillow e numpy); outra precisa
  de motivo no pull request.
- Detector novo no conferidor entra com as duas provas: um caso plantado em `provas/plantado/` que ele pega e zero falso positivo em `provas/limpo/` e nos `exemplos/` (`python provas.py`).
- Todo caso novo tem teste ou prova, com o resultado esperado escrito à mão no
  próprio teste.
- Exemplos e testes só com dados inventados: nada de dado real de pessoa ou
  de empresa.
- Código, mensagens e documentação em português do Brasil.
- Mudança de comportamento entra no [CHANGELOG.md](CHANGELOG.md).
- Código próprio: não traga código copiado de outro projeto, mesmo de
  licença livre. O que você contribui sai sob a [licença MIT](LICENSE) do
  projeto.
