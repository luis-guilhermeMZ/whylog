from pathlib import Path

import pytest

from whylog.decision import (
    Decision,
    create_decision,
    decision_filename,
    from_markdown,
    list_decisions,
    slugify,
    to_markdown,
)


@pytest.mark.parametrize("tags", [[], ["backend", "cache"]])
def test_create_markdown_round_trip(tmp_path: Path, tags: list[str]) -> None:
    decision = create_decision("Teste", "Escolher X", "Motivo", ["Y"], tags=tags)
    decision.substituida_por = "outra.md"
    path = tmp_path / "teste.md"
    path.write_text(to_markdown(decision), encoding="utf-8")
    parsed = from_markdown(path)
    assert parsed.titulo == decision.titulo
    assert parsed.data == decision.data
    assert parsed.tags == tags
    assert parsed.decisao == decision.decisao
    assert parsed.motivo == decision.motivo
    assert parsed.alternativas == decision.alternativas
    assert parsed.substituida_por == "outra.md"


def test_round_trip_without_substituida_por() -> None:
    assert "substituida_por:" not in to_markdown(create_decision("Teste", "X", "Y", []))


def test_slugify_removes_accents() -> None:
    assert slugify("Decisão sobre cache") == "decisao-sobre-cache"


def test_decision_filename_avoids_collisions(tmp_path: Path) -> None:
    decision = Decision("Decisão sobre cache", "2026-01-01", "ativa", [], "x", "y", [])
    first = Path(decision_filename(decision, str(tmp_path)))
    first.touch()
    second = Path(decision_filename(decision, str(tmp_path)))
    assert second.name == "2026-01-01-decisao-sobre-cache-2.md"


def test_frontmatter_does_not_consume_body_separator(tmp_path: Path) -> None:
    path = tmp_path / "body.md"
    content = (
        "---\ntitulo: Separador\nstatus: ativa\n---\n## Decisão\nA\n---\nB\n"
        "## Motivo\nRazão\n## Alternativas descartadas\n- C\n"
    )
    path.write_text(content, encoding="utf-8")
    parsed = from_markdown(path)
    assert parsed.decisao == "A\n---\nB"
    assert parsed.motivo == "Razão"


def test_malformed_and_empty_files_use_defaults(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.md"
    empty = tmp_path / "empty.md"
    malformed.write_text("---\ntitulo sem valor válido\n## Decisão\nOk\n", encoding="utf-8")
    empty.write_text("", encoding="utf-8")
    assert from_markdown(malformed).titulo == "malformed"
    assert from_markdown(empty).status == "ativa"
    assert from_markdown(empty).decisao == ""
    assert list_decisions(str(tmp_path))


def test_list_decisions_empty_and_missing(tmp_path: Path) -> None:
    assert list_decisions(str(tmp_path / "missing")) == []
    existing = tmp_path / "empty"
    existing.mkdir()
    assert list_decisions(str(existing)) == []
