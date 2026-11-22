"""Integração com APIs compatíveis com OpenAI e com Gemini nativo."""

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
    """Carrega variáveis simples do .env sem substituir o ambiente."""
    dotenv_path = Path(path)
    if not dotenv_path.is_file():
        return
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


def get_config() -> dict[str, str]:
    """Retorna configuração, priorizando variáveis já exportadas."""
    _load_dotenv()
    return {
        "api_key": os.environ.get("WHYLOG_API_KEY", ""),
        "base_url": os.environ.get("WHYLOG_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "model": os.environ.get("WHYLOG_MODEL", DEFAULT_MODEL),
    }


def _safe_body(response: requests.Response, api_key: str) -> str:
    """Retorna trecho de erro sem reproduzir a chave configurada."""
    body = str(getattr(response, "text", ""))[:300]
    if api_key:
        body = body.replace(api_key, "[chave ocultada]")
    return body


def _post(url: str, headers: dict[str, str], body: dict, model: str, api_key: str) -> dict:
    """Faz a chamada HTTP e contextualiza falhas sem revelar credenciais."""
    try:
        response = requests.post(url, headers=headers, json=body, timeout=60)
    except requests.RequestException as exc:
        safe_message = str(exc).replace(api_key, "[chave ocultada]") if api_key else str(exc)
        raise RuntimeError(
            f"Falha de conexão com a API para o modelo '{model}' em {url}: {safe_message}"
        ) from exc
    if not response.ok:
        raise RuntimeError(
            f"API retornou HTTP {response.status_code} para o modelo '{model}' em {url}: "
            f"{_safe_body(response, api_key)}"
        )
    try:
        return response.json()
    except (ValueError, requests.RequestException) as exc:
        raise RuntimeError(
            f"Resposta inválida da API para o modelo '{model}' em {url}: "
            f"{_safe_body(response, api_key)}"
        ) from exc


def _ask_gemini(cfg: dict[str, str], msg: str) -> str:
    """Consulta o endpoint nativo generateContent do Gemini."""
    base = cfg["base_url"]
    if base.endswith("/openai"):
        base = base[: -len("/openai")]
    model = cfg["model"].removeprefix("models/")
    url = f"{base}/models/{model}:generateContent"
    data = _post(
        url,
        {"x-goog-api-key": cfg["api_key"]},
        {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": msg}]}],
        },
        model,
        cfg["api_key"],
    )
    candidates = data.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    answer = "".join(part.get("text", "") for part in parts).strip()
    if not answer:
        feedback = data.get("promptFeedback") or {}
        reason = feedback.get("blockReason")
        if reason:
            raise RuntimeError(f"A solicitação foi bloqueada pelo Gemini (motivo: {reason}).")
        finish_reason = candidates[0].get("finishReason") if candidates else None
        detail = finish_reason or "resposta sem texto ou candidatos"
        raise RuntimeError(f"O Gemini não devolveu texto (motivo: {detail}).")
    return answer


def _ask_openai(cfg: dict[str, str], msg: str) -> str:
    """Consulta endpoint /chat/completions compatível com OpenAI."""
    url = f"{cfg['base_url']}/chat/completions"
    data = _post(
        url,
        {"Authorization": f"Bearer {cfg['api_key']}"},
        {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg},
            ],
        },
        cfg["model"],
        cfg["api_key"],
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Resposta sem texto da API para o modelo '{cfg['model']}' em {url}."
        ) from exc


def ask(question: str, context: str) -> str:
    """Envia pergunta e contexto ao provedor configurado."""
    cfg = get_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "WHYLOG_API_KEY não configurada. Crie o arquivo .env na raiz do projeto "
            "(veja .env.example) com suas credenciais."
        )
    message = f"Pergunta: {question}\n\nContexto das decisões:\n{context}"
    if GEMINI_HOST in cfg["base_url"]:
        return _ask_gemini(cfg, message)
    return _ask_openai(cfg, message)
