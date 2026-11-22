from pathlib import Path

from whylog import cli


def test_add_non_interactive_and_list(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert (
        cli.main(
            [
                "add",
                "--titulo",
                "Decisão",
                "--decisao",
                "X",
                "--motivo",
                "Y",
                "--alternativas",
                "A,B",
                "--tags",
                "t1,t2",
            ]
        )
        == 0
    )
    assert "Decisão registrada em decisions/" in capsys.readouterr().out
    assert cli.main(["list"]) == 0
    assert "[ativa]" in capsys.readouterr().out


def test_list_empty(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["list"]) == 0
    assert "Nenhuma decisão registrada ainda." in capsys.readouterr().out


def test_show(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["add", "--titulo", "Mostrar", "--decisao", "A", "--motivo", "B"])
    assert cli.main(["show", "decisions/2026-11-22-mostrar.md"]) == 0
    assert "## Decisão" in capsys.readouterr().out


def test_supersede_success_and_already_superseded(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    cli.main(["add", "--titulo", "Antiga", "--decisao", "A", "--motivo", "B"])
    path = Path("decisions/2026-11-22-antiga.md")
    original_body = path.read_text(encoding="utf-8").split("---\n", 2)[-1]
    assert cli.main(["supersede", path.name, "--por", "nova.md"]) == 0
    content = path.read_text(encoding="utf-8")
    assert "status: substituida" in content
    assert "substituida_por: nova.md" in content
    assert content.split("---\n", 2)[-1] == original_body
    assert cli.main(["supersede", path.name]) == 1
    assert "já está substituída" in capsys.readouterr().err


def test_supersede_missing_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["supersede", "nao-existe.md"]) == 1
    assert "não encontrado" in capsys.readouterr().err


def test_show_missing_file(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["show", "nao-existe.md"]) == 1
    assert "não encontrado" in capsys.readouterr().err


def test_ask_without_decisions(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["ask", "pergunta"]) == 0
    assert "Não encontrei nenhuma decisão" in capsys.readouterr().out


def test_ask_without_key(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WHYLOG_API_KEY", raising=False)
    cli.main(["add", "--titulo", "Pergunta", "--decisao", "X", "--motivo", "Y"])
    assert cli.main(["ask", "pergunta"]) == 1
    assert "WHYLOG_API_KEY não configurada" in capsys.readouterr().out


def test_ask_empty_question_is_usage_error(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(["ask", "   "]) == 2
    assert "pergunta não vazia" in capsys.readouterr().err
