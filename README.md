# Whylog

Ferramenta de linha de comando que guarda as decisões técnicas de um projeto e responde perguntas sobre elas.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso

- `whylog add` — registra uma decisão (título, decisão, motivo, alternativas descartadas e tags)
- `whylog list` — lista as decisões registradas
- `whylog ask '<pergunta>'` — pergunta sobre as decisões do projeto

As decisões ficam em `decisions/*.md`. Rode os comandos na raiz do projeto.

## Configuração

Copie `.env.example` para `.env` na raiz do projeto e preencha:

```
WHYLOG_API_KEY=
WHYLOG_BASE_URL=
WHYLOG_MODEL=
```

Variáveis já exportadas no shell têm prioridade sobre o `.env`.

Funciona com qualquer API compatível com OpenAI (`/chat/completions`), como OpenAI e Google Gemini. Os exemplos estão no `.env.example`.

## Solução de problemas

- **404 Not Found:** quase sempre é o nome do modelo, que pode ter sido desligado pelo provedor. A mensagem de erro mostra o modelo e o corpo da resposta da API.
- **401 Unauthorized:** a chave não combina com o provedor da `WHYLOG_BASE_URL`.
