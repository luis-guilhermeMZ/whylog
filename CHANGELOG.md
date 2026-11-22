# Changelog

As mudanças notáveis deste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e o projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.2.0] - 2026-11-22

### Adicionado

- Comandos `show` e `supersede`, além de flags para criação não interativa.
- Frontmatter opcional `substituida_por` e tratamento de arquivos incompletos.
- Testes automatizados, lint, CI e documentação de publicação.
- Suporte de erro de rede amigável e diagnóstico seguro para APIs.

### Corrigido

- Slugs agora removem acentos corretamente e colisões não sobrescrevem decisões.
- Parsing limita o frontmatter ao primeiro bloco no início do arquivo.
- Ausência do executável Git não interrompe `ask`.

## [0.1.0] - 2026-11-21

### Adicionado

- MVP com `add`, `list` e `ask`, decisões Markdown, wikilinks e contexto do Git.
- Integração com endpoints compatíveis com OpenAI e endpoint nativo do Gemini.
- Configuração por variáveis de ambiente e arquivo `.env`.
