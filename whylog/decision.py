"""Modelo de decisão do Whylog.

Representa uma decisão técnica registrada em decisions/*.md, com
frontmatter no formato fixo e corpo em seções.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DECISION_STATUS_ATIVA = "ativa"
DECISION_STATUS_SUBSTITUIDA = "substituida"

DECISIONS_DIR = "decisions"

DECISION_SECTION_DECISAO = "decisão"
DECISION_SECTION_MOTIVO = "motivo"
DECISION_SECTION_ALTERNATIVAS = "alternativas descartadas"

KNOWN_FRONTMATTER_KEYS = ("titulo", "data", "status", "tags")


@dataclass
class Decision:
    titulo: str
    data: str
    status: str
    tags: list
    decisao: str
    motivo: str
    alternativas: list
    arquivo: str = ""


def create_decision(
    titulo: str,
    decisao: str,
    motivo: str,
    alternativas: list,
    status: str = DECISION_STATUS_ATIVA,
    tags: list | None = None,
) -> Decision:
    """Cria uma Decision com a data de hoje e o status informado."""
    return Decision(
        titulo=titulo.strip(),
        data=date.today().isoformat(),
        status=status,
        tags=list(tags or []),
        decisao=decisao.strip(),
        motivo=motivo.strip(),
        alternativas=list(alternativas or []),
    )


def slugify(text: str) -> str:
    """Converte um título em slug para o nome do arquivo."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "decisao"


def decision_filename(decisao: Decision, decisions_dir: str = DECISIONS_DIR) -> str:
    """Retorna o caminho do arquivo da decisão, ex: decisions/2026-11-21-escolha.md"""
    return f"{decisions_dir}/{decisao.data}-{slugify(decisao.titulo)}.md"


def to_markdown(decisao: Decision) -> str:
    """Serializa a Decision para o formato .md com frontmatter fixo."""
    tags_str = ", ".join(decisao.tags)
    alternativas = "\n".join(f"- {item}" for item in decisao.alternativas)
    return (
        f"---\n"
        f"titulo: {decisao.titulo}\n"
        f"data: {decisao.data}\n"
        f"status: {decisao.status}\n"
        f"tags: [{tags_str}]\n"
        f"---\n"
        f"\n"
        f"## Decisão\n"
        f"\n"
        f"{decisao.decisao}\n"
        f"\n"
        f"## Motivo\n"
        f"\n"
        f"{decisao.motivo}\n"
        f"\n"
        f"## Alternativas descartadas\n"
        f"\n"
        f"{alternativas}\n"
    )


def _parse_frontmatter(lines: list) -> dict:
    """Extrai apenas as chaves conhecidas; ignora linhas desconhecidas."""
    data: dict = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in KNOWN_FRONTMATTER_KEYS:
            continue
        data[key] = value.strip()
    return data


def _parse_sections(body: str) -> dict:
    """Extrai as seções do corpo ('' se a seção não existir)."""
    sections: dict = {}
    current_key = None
    current_lines: list = []

    def flush() -> None:
        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

    for line in body.splitlines():
        stripped = line.strip()
        matched = False
        for key in (
            DECISION_SECTION_DECISAO,
            DECISION_SECTION_MOTIVO,
            DECISION_SECTION_ALTERNATIVAS,
        ):
            if stripped.lower().startswith(f"## {key}"):
                flush()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched and current_key is not None:
            current_lines.append(line)
    flush()
    return sections


def _parse_tags(value: str) -> list:
    """Converte o valor do frontmatter (ex: '[a, b]' ou 'a, b') em lista."""
    value = (value or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    value = value.strip()
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _parse_alternativas(text: str) -> list:
    """Extrai a lista de alternativas descartadas a partir do corpo."""
    if not text:
        return []
    return [
        line.strip()[2:].strip()
        for line in text.splitlines()
        if line.strip().startswith("- ")
    ]


def list_decisions(decisions_dir: str = DECISIONS_DIR) -> list[Decision]:
    """Lista todas as decisões (.md) registradas em decisions_dir."""
    directory = Path(decisions_dir)
    if not directory.is_dir():
        return []
    return [from_markdown(path) for path in sorted(directory.glob("*.md"))]


def from_markdown(path: Path) -> Decision:
    """Lê um arquivo .md de decisão e retorna o Decision correspondente."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    frontmatter_lines: list = []
    body_lines: list = []
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            in_frontmatter = False
            continue
        if in_frontmatter:
            frontmatter_lines.append(line)
        else:
            body_lines.append(line)

    frontmatter = _parse_frontmatter(frontmatter_lines)
    sections = _parse_sections("\n".join(body_lines))

    return Decision(
        titulo=frontmatter.get("titulo") or path.stem,
        data=frontmatter.get("data") or "",
        status=frontmatter.get("status") or DECISION_STATUS_ATIVA,
        tags=_parse_tags(frontmatter.get("tags") or ""),
        decisao=sections.get(DECISION_SECTION_DECISAO, ""),
        motivo=sections.get(DECISION_SECTION_MOTIVO, ""),
        alternativas=_parse_alternativas(sections.get(DECISION_SECTION_ALTERNATIVAS, "")),
        arquivo=str(path),
    )
