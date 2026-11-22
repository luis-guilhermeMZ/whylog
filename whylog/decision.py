"""Modelo e serialização de decisões técnicas."""

import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DECISION_STATUS_ATIVA = "ativa"
DECISION_STATUS_SUBSTITUIDA = "substituida"
DECISIONS_DIR = "decisions"
DECISION_SECTION_DECISAO = "decisão"
DECISION_SECTION_MOTIVO = "motivo"
DECISION_SECTION_ALTERNATIVAS = "alternativas descartadas"
KNOWN_FRONTMATTER_KEYS = ("titulo", "data", "status", "tags", "substituida_por")


@dataclass
class Decision:
    """Decisão técnica com campos compatíveis com os arquivos Markdown existentes."""

    titulo: str
    data: str
    status: str
    tags: list[str]
    decisao: str
    motivo: str
    alternativas: list[str]
    arquivo: str = ""
    substituida_por: str = ""


def create_decision(
    titulo: str,
    decisao: str,
    motivo: str,
    alternativas: list[str],
    status: str = DECISION_STATUS_ATIVA,
    tags: list[str] | None = None,
) -> Decision:
    """Cria uma decisão datada de hoje."""
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
    """Converte texto em slug ASCII, preservando letras acentuadas sem acento."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.strip().lower()).strip("-")
    return slug or "decisao"


def decision_filename(decisao: Decision, decisions_dir: str = DECISIONS_DIR) -> str:
    """Gera um caminho livre sem sobrescrever uma decisão existente."""
    directory = Path(decisions_dir)
    stem = f"{decisao.data}-{slugify(decisao.titulo)}"
    candidate = directory / f"{stem}.md"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{suffix}.md"
        suffix += 1
    return str(candidate)


def to_markdown(decisao: Decision) -> str:
    """Serializa a decisão no formato Markdown do Whylog."""
    tags_str = ", ".join(decisao.tags)
    alternativas = "\n".join(f"- {item}" for item in decisao.alternativas)
    substituida = f"substituida_por: {decisao.substituida_por}\n" if decisao.substituida_por else ""
    return (
        "---\n"
        f"titulo: {decisao.titulo}\n"
        f"data: {decisao.data}\n"
        f"status: {decisao.status}\n"
        f"tags: [{tags_str}]\n"
        f"{substituida}"
        "---\n\n"
        "## Decisão\n\n"
        f"{decisao.decisao}\n\n"
        "## Motivo\n\n"
        f"{decisao.motivo}\n\n"
        "## Alternativas descartadas\n\n"
        f"{alternativas}\n"
    )


def _parse_frontmatter(lines: list[str]) -> dict[str, str]:
    """Lê chaves conhecidas e ignora linhas inválidas."""
    data: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in KNOWN_FRONTMATTER_KEYS:
            data[key] = value.strip()
    return data


def _parse_sections(body: str) -> dict[str, str]:
    """Extrai seções do corpo sem tratar separadores Markdown como frontmatter."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

    for line in body.splitlines():
        stripped = line.strip().lower()
        key = next(
            (
                name
                for name in (
                    DECISION_SECTION_DECISAO,
                    DECISION_SECTION_MOTIVO,
                    DECISION_SECTION_ALTERNATIVAS,
                )
                if stripped.startswith(f"## {name}")
            ),
            None,
        )
        if key is not None:
            flush()
            current_key = key
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)
    flush()
    return sections


def _parse_tags(value: str) -> list[str]:
    """Converte tags separadas por vírgula em lista."""
    value = (value or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [tag.strip().strip("\"'") for tag in value.split(",") if tag.strip()]


def _parse_alternativas(text: str) -> list[str]:
    """Extrai itens de lista da seção de alternativas."""
    return [line.strip()[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")]


def list_decisions(decisions_dir: str = DECISIONS_DIR) -> list[Decision]:
    """Lista arquivos Markdown válidos, ignorando arquivos ilegíveis com aviso."""
    directory = Path(decisions_dir)
    if not directory.is_dir():
        return []
    decisions: list[Decision] = []
    for path in sorted(directory.glob("*.md")):
        try:
            decisions.append(from_markdown(path))
        except (OSError, UnicodeError) as exc:
            print(f"Aviso: não foi possível ler {path.name}: {exc}", file=sys.stderr)
    return decisions


def from_markdown(path: Path) -> Decision:
    """Lê o primeiro frontmatter no início e aplica padrões a campos ausentes."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    frontmatter_lines: list[str] = []
    body_lines = lines
    if lines and lines[0].strip() == "---":
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if closing is not None:
            frontmatter_lines = lines[1:closing]
            body_lines = lines[closing + 1 :]
    frontmatter = _parse_frontmatter(frontmatter_lines)
    sections = _parse_sections("\n".join(body_lines))
    return Decision(
        titulo=frontmatter.get("titulo") or path.stem,
        data=frontmatter.get("data", ""),
        status=frontmatter.get("status") or DECISION_STATUS_ATIVA,
        tags=_parse_tags(frontmatter.get("tags", "")),
        decisao=sections.get(DECISION_SECTION_DECISAO, ""),
        motivo=sections.get(DECISION_SECTION_MOTIVO, ""),
        alternativas=_parse_alternativas(sections.get(DECISION_SECTION_ALTERNATIVAS, "")),
        arquivo=str(path),
        substituida_por=frontmatter.get("substituida_por", ""),
    )
