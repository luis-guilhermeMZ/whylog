import os
from types import SimpleNamespace

import pytest
import requests

from whylog import llm


def response(payload: dict, status: int = 200, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(ok=status < 400, status_code=status, text=text, json=lambda: payload)


def test_gemini_native_request(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHYLOG_API_KEY", "test-key")
    monkeypatch.setenv("WHYLOG_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setenv("WHYLOG_MODEL", "models/gemini-test")
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return response({"candidates": [{"content": {"parts": [{"text": "Resposta"}]}}]})

    monkeypatch.setattr(llm.requests, "post", post)
    assert llm.ask("Pergunta", "Contexto") == "Resposta"
    url, kwargs = calls[0]
    assert (
        url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
    )
    assert kwargs["headers"] == {"x-goog-api-key": "test-key"}
    assert "systemInstruction" in kwargs["json"]
    assert "Pergunta" in kwargs["json"]["contents"][0]["parts"][0]["text"]


def test_gemini_blocked_response(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHYLOG_API_KEY", "test-key")
    monkeypatch.setenv("WHYLOG_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    monkeypatch.setattr(
        llm.requests,
        "post",
        lambda *args, **kwargs: response({"promptFeedback": {"blockReason": "SAFETY"}}),
    )
    with pytest.raises(RuntimeError, match="bloqueada.*SAFETY"):
        llm.ask("Pergunta", "Contexto")


def test_openai_compatible_request(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHYLOG_API_KEY", "test-key")
    monkeypatch.setenv("WHYLOG_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("WHYLOG_MODEL", "modelo")
    calls = []
    monkeypatch.setattr(
        llm.requests,
        "post",
        lambda url, **kwargs: (
            calls.append((url, kwargs)) or response({"choices": [{"message": {"content": "Ok"}}]})
        ),
    )
    assert llm.ask("Q", "C") == "Ok"
    assert calls[0][0] == "https://example.test/v1/chat/completions"
    assert calls[0][1]["headers"] == {"Authorization": "Bearer test-key"}
    assert calls[0][1]["json"]["model"] == "modelo"


def test_http_error_does_not_leak_key(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHYLOG_API_KEY", "secret-key")
    monkeypatch.setenv("WHYLOG_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setattr(
        llm.requests, "post", lambda *args, **kwargs: response({}, 401, "bad secret-key")
    )
    with pytest.raises(RuntimeError) as error:
        llm.ask("Q", "C")
    assert "HTTP 401" in str(error.value)
    assert "modelo" in str(error.value)
    assert "https://api.openai.com/v1/chat/completions" in str(error.value)
    assert "secret-key" not in str(error.value)


def test_network_error_is_friendly(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WHYLOG_API_KEY", "secret-key")

    def fail(*args, **kwargs):
        raise requests.Timeout("timeout secret-key")

    monkeypatch.setattr(llm.requests, "post", fail)
    with pytest.raises(RuntimeError, match="Falha de conexão") as error:
        llm.ask("Q", "C")
    assert "secret-key" not in str(error.value)


def test_dotenv_does_not_override_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / ".env"
    path.write_text("WHYLOG_API_KEY=dotenv-key\nWHYLOG_MODEL=dotenv-model\n", encoding="utf-8")
    monkeypatch.setenv("WHYLOG_API_KEY", "shell-key")
    monkeypatch.delenv("WHYLOG_MODEL", raising=False)
    llm._load_dotenv(str(path))
    assert os.environ["WHYLOG_API_KEY"] == "shell-key"
    assert os.environ["WHYLOG_MODEL"] == "dotenv-model"
