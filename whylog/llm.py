"""Integração com a API do modelo via variáveis de ambiente."""

import os

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "Você é o Whylog, uma ferramenta que responde perguntas sobre decisões técnicas "
    "de um projeto. Responda com base apenas no contexto fornecido. "
    "Cite o arquivo da decisão utilizada (ex: decisions/2026-11-21-foo.md). "
    "Prefira decisões com status 'ativa'; se for relevante citar uma com status "
    "'substituida', avise que ela foi substituída."
)


def get_config() -> dict:
    return {
        "api_key": os.environ.get("WHYLOG_API_KEY", ""),
        "base_url": os.environ.get("WHYLOG_BASE_URL", DEFAULT_BASE_URL),
        "model": os.environ.get("WHYLOG_MODEL", DEFAULT_MODEL),
    }


def ask(question: str, context: str) -> str:
    """Envia a pergunta + contexto ao modelo e retorna a resposta."""
    config = get_config()
    if not config["api_key"]:
        raise RuntimeError(
            "WHYLOG_API_KEY não configurada. Crie o arquivo .env na raiz do projeto "
            "(veja .env.example) com suas credenciais."
        )
    response = requests.post(
        f"{config['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {config['api_key']}"},
        json={
            "model": config["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Pergunta: {question}\n\nContexto das decisões:\n{context}",
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
