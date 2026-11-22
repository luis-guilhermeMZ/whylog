"""Integração com a API do modelo (OpenAI-compatível ou Gemini nativo)."""

import os
from pathlib import Path

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
GEMINI_HOST = "generativelanguage.googleapis.com"

SYSTEM_PROMPT = (
    "Você é o Whylog, uma ferramenta que responde perguntas sobre decisões técnicas "
    "de um projeto. Responda com base apenas no contexto fornecido. "
    "Cite o arquivo da decisão utilizada (ex: decisions/2026-11-21-foo.md). "
    "Prefira decisões com status 'ativa'; se for relevante citar uma com status "
    "'substituida', avise que ela foi substituída."
)


def _load_dotenv(path: str = ".env") -> None:
    f = Path(path)
    if not f.is_file():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v:
            os.environ.setdefault(k, v)


def get_config() -> dict:
    _load_dotenv()
    return {
        "api_key": os.environ.get("WHYLOG_API_KEY", ""),
        "base_url": os.environ.get("WHYLOG_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "model": os.environ.get("WHYLOG_MODEL", DEFAULT_MODEL),
    }


def _post(url: str, headers: dict, body: dict, model: str) -> dict:
    r = requests.post(url, headers=headers, json=body, timeout=60)
    if not r.ok:
        raise RuntimeError(
            f"API retornou {r.status_code} para o modelo '{model}' em {url}: {r.text[:300]}"
        )
    return r.json()


def _ask_gemini(cfg: dict, msg: str) -> str:
    base = cfg["base_url"]
    if base.endswith("/openai"):
        base = base[: -len("/openai")]
    model = cfg["model"].removeprefix("models/")
    data = _post(
        f"{base}/models/{model}:generateContent",
        {"x-goog-api-key": cfg["api_key"]},
        {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": msg}]}],
        },
        model,
    )
    cands = data.get("candidates") or []
    parts = cands[0].get("content", {}).get("parts", []) if cands else []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        why = (data.get("promptFeedback") or {}).get("blockReason") or (
            cands[0].get("finishReason") if cands else "sem candidatos"
        )
        raise RuntimeError(f"O modelo não devolveu texto (motivo: {why}).")
    return text


def _ask_openai(cfg: dict, msg: str) -> str:
    data = _post(
        f"{cfg['base_url']}/chat/completions",
        {"Authorization": f"Bearer {cfg['api_key']}"},
        {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg},
            ],
        },
        cfg["model"],
    )
    return data["choices"][0]["message"]["content"]


def ask(question: str, context: str) -> str:
    """Envia a pergunta + contexto ao modelo e retorna a resposta."""
    cfg = get_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "WHYLOG_API_KEY não configurada. Crie o arquivo .env na raiz do projeto "
            "(veja .env.example) com suas credenciais."
        )
    msg = f"Pergunta: {question}\n\nContexto das decisões:\n{context}"
    if GEMINI_HOST in cfg["base_url"]:
        return _ask_gemini(cfg, msg)
    return _ask_openai(cfg, msg)
