# Whylog

Ferramenta de linha de comando que guarda as decisões técnicas de um projeto e responde perguntas sobre elas.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso

- `whylog add` — registra uma decisão (título, decisão, motivo e alternativas descartadas)
- `whylog list` — lista as decisões registradas
- `whylog ask '<pergunta>'` — pergunta sobre as decisões do projeto

## Configuração

Crie um arquivo `.env` na raiz do projeto com suas credenciais:

```
WHYLOG_API_KEY=
WHYLOG_BASE_URL=
WHYLOG_MODEL=
```
