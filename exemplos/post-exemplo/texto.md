selo: EXEMPLO · conteúdo fictício
rodape: @seu.perfil · exemplo do carrossel-terminal

> Post de exemplo: conteúdo neutro, sem número que precise de fonte.
> Linhas com ">" são notas de conferência: ficam no texto.md, não vão para a imagem.

--- slide capa
// exemplo
# Revise o commit antes do push
## três hábitos que cabem em um minuto
Um carrossel curto, gerado a partir de um texto.md.

--- slide
// hábito 1
# Leia o diff inteiro
- Rode `git diff --staged` antes de commitar
- Procure o que **não** devia estar ali
- Arquivo esquecido, `print` de depuração, senha
> Nota de conferência: o comando é o mesmo em qualquer sistema.

--- slide
// hábito 2
# Um assunto por commit
| em vez de | prefira |
|---|---|
| "ajustes" | "corrige a data do rodapé" |
| tudo junto | um assunto por vez |

--- slide
// ! hábito 3
# Rode os testes de novo
- O teste que passou ontem não vale para o código de hoje
- **Teste vermelho** não sobe: !!conserte antes!!

--- slide
// resumo
# Antes do push
- Leia o diff
- Um assunto por commit
- Testes verdes
Salve para a próxima revisão.
