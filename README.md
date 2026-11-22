# whylog

CLI em Python para registrar decisões técnicas como Markdown e consultar o histórico do projeto em linguagem natural usando uma API de modelos de linguagem.

## Por que existe

Decisões importantes se perdem em conversas, pull requests e na memória da equipe. O whylog mantém cada escolha em `decisions/`, num formato simples compatível com Obsidian, e reúne decisões relacionadas antes de responder perguntas.

## Instalação

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## Configuração

Copie `.env.example` para `.env` na raiz do projeto e configure um provedor. Variáveis exportadas no shell sempre têm prioridade sobre valores de `.env`.

OpenAI:

```dotenv
WHYLOG_API_KEY=sua-chave
WHYLOG_BASE_URL=https://api.openai.com/v1
WHYLOG_MODEL=gpt-4o-mini
```

Gemini nativo:

```dotenv
WHYLOG_API_KEY=sua-chave
WHYLOG_BASE_URL=https://generativelanguage.googleapis.com/v1beta
WHYLOG_MODEL=gemini-2.5-flash
```

Também funciona com endpoints compatíveis com OpenAI. O whylog detecta o host do Gemini e usa `:generateContent`; se a URL terminar em `/openai`, esse sufixo é removido para a chamada nativa.

## Comandos

Execute os comandos na raiz do projeto.

### `whylog add`

O modo interativo pergunta título, decisão, motivo, alternativas e tags. Para scripts, informe os campos por flags:

```bash
whylog add --titulo "Cache de respostas" \
  --decisao "Usar Redis" --motivo "Reduzir latência" \
  --alternativas "cache em memória,sem cache" --tags "backend,performance"
```

Exemplo de saída:

```text
Decisão registrada em decisions/2026-11-22-cache-de-respostas.md
```

Colisões de título e data geram sufixos `-2`, `-3` etc., sem sobrescrever arquivos.

### `whylog list`

```text
- [ativa] 2026-11-22-cache-de-respostas.md — Cache de respostas (tags: backend, performance)
```

Se não houver decisões: `Nenhuma decisão registrada ainda.`

### `whylog show <arquivo>`

Aceita o nome do arquivo dentro de `decisions/` ou um caminho completo:

```bash
whylog show 2026-11-22-cache-de-respostas.md
```

Imprime o conteúdo formatado da decisão.

### `whylog supersede <arquivo> [--por <arquivo-novo>]`

Marca a decisão como substituída. O caminho informado em `--por` é gravado em `substituida_por`:

```bash
whylog supersede 2026-11-21-escolha-do-banco.md --por 2026-11-22-postgresql-gerenciado.md
```

### `whylog ask "<pergunta>"`

```bash
whylog ask "Qual banco foi escolhido e por quê?"
```

A consulta reúne as decisões, segue referências `[[nome-do-arquivo]]` entre elas e anexa os últimos 20 commits de `git log --oneline`. Se o Git não estiver instalado ou não houver histórico, a consulta segue com uma indicação de log vazio. Sem decisões, o comando informa isso sem chamar a API. Uma pergunta vazia é erro de uso.

## Formato das decisões

Cada arquivo em `decisions/` usa frontmatter fixo, compatível com Obsidian:

```markdown
---
titulo: Escolha do banco de dados
data: 2026-11-21
status: ativa
tags: [banco-de-dados, backend]
---

## Decisão

Usar PostgreSQL.

## Motivo

Suporte a JSONB e experiência da equipe.

## Alternativas descartadas

- MySQL
- SQLite
```

Quando uma decisão é substituída, `status` passa a `substituida` e, se fornecido, o frontmatter também contém `substituida_por: nome-do-arquivo.md`. Esse campo é opcional; arquivos anteriores continuam válidos.

## Solução de problemas

- **404:** confira `WHYLOG_MODEL`, o endpoint e se o modelo ainda está ativo na conta. Provedores podem desligar ou renomear modelos.
- **401/403:** confira se a chave pertence ao provedor da URL e se a conta tem acesso ao modelo. A mensagem mostra status, modelo, URL e um trecho da resposta, sem expor a chave.
- **Gemini `401 ACCESS_TOKEN_TYPE_UNSUPPORTED`:** algumas contas rejeitam chaves Google com prefixo `AQ.` nesse endpoint. É um problema do tipo de chave/conta; use uma chave compatível ou outro provedor com API compatível com OpenAI.
- **Falha de conexão/timeout:** verifique rede, proxy, URL base e disponibilidade do serviço.
- **Sem chave:** configure `WHYLOG_API_KEY` no ambiente ou em `.env` local.

## Desenvolvimento

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
```

Testes usam mocks e não chamam a rede.

## Roadmap

- Melhorar navegação entre decisões relacionadas.
- Avaliar busca local por relevância quando o acervo crescer.
- Refinar o suporte a provedores compatíveis com OpenAI.

## Licença

MIT. Consulte [LICENSE](LICENSE).
