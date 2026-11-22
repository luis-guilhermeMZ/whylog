"""Interface de linha de comando do Whylog."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

from whylog import __version__
from whylog.decision import (
    DECISION_STATUS_SUBSTITUIDA,
    DECISIONS_DIR,
    Decision,
    create_decision,
    decision_filename,
    from_markdown,
    list_decisions,
    to_markdown,
)
from whylog.llm import ask

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:[|][^]]*)?\]\]")


def _split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _cmd_add(args: argparse.Namespace) -> int:
    if args.titulo is None:
        titulo = input("Título da decisão: ").strip()
        decisao = input("Decisão: ").strip()
        motivo = input("Motivo: ").strip()
        alternativas = _split_csv(input("Alternativas descartadas (separadas por vírgula): "))
        tags = _split_csv(input("Tags (separadas por vírgula, opcionais): "))
    else:
        titulo, decisao, motivo = args.titulo.strip(), args.decisao.strip(), args.motivo.strip()
        alternativas, tags = _split_csv(args.alternativas), _split_csv(args.tags)
    if not titulo or not decisao or not motivo:
        print("Erro: título, decisão e motivo não podem ficar vazios.", file=sys.stderr)
        return 2
    nova_decisao = create_decision(titulo, decisao, motivo, alternativas, tags=tags)
    path = Path(decision_filename(nova_decisao, DECISIONS_DIR))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_markdown(nova_decisao), encoding="utf-8")
    print(f"Decisão registrada em {path}")
    return 0


def _cmd_list() -> int:
    decisions = list_decisions(DECISIONS_DIR)
    if not decisions:
        print("Nenhuma decisão registrada ainda.")
        return 0
    for d in decisions:
        tags = ", ".join(d.tags) if d.tags else "-"
        print(f"- [{d.status}] {Path(d.arquivo).name} — {d.titulo} (tags: {tags})")
    return 0


def _decision_text(d: Decision) -> str:
    parts = [d.titulo, d.decisao, d.motivo, "\n".join(d.alternativas)]
    return "\n".join(str(part) for part in parts if str(part).strip())


def _git_log_recent(limit: int = 20) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{limit}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _build_context(decisions: list[Decision]) -> str:
    blocks: list[str] = []
    used: set[str] = set()
    by_name = {Path(decision.arquivo).name: decision for decision in decisions}

    def add(decision: Decision) -> None:
        key = Path(decision.arquivo).name
        if key in used:
            return
        used.add(key)
        block = f"Arquivo: {key}\nStatus: {decision.status}"
        if decision.tags:
            block += f"\nTags: {', '.join(decision.tags)}"
        block += f"\nDecisão: {decision.decisao}\nMotivo: {decision.motivo}"
        if decision.alternativas:
            block += "\nAlternativas descartadas: " + "; ".join(decision.alternativas)
        blocks.append(block)
        for link in WIKILINK_RE.findall(_decision_text(decision)):
            target = link.strip()
            target_name = target if target.endswith(".md") else f"{target}.md"
            linked = by_name.get(target_name)
            if linked:
                add(linked)

    for decision in decisions:
        add(decision)
    context = "\n\n".join(blocks)
    git_log = _git_log_recent()
    return context + "\n\n## Git log recente\n" + (git_log or "(nenhum commit encontrado)")


def _cmd_ask(args: argparse.Namespace) -> int:
    if not args.question.strip():
        print("Erro de uso: informe uma pergunta não vazia.", file=sys.stderr)
        return 2
    decisions = list_decisions(DECISIONS_DIR)
    if not decisions:
        print("Não encontrei nenhuma decisão registrada em decisions/ para responder.")
        return 0
    try:
        answer = ask(args.question, _build_context(decisions))
    except Exception as exc:
        print(f"Não foi possível consultar o modelo: {exc}")
        return 1
    print(answer)
    return 0


def _find_decision_file(value: str) -> Path | None:
    supplied = Path(value)
    candidates = [supplied]
    if not supplied.is_absolute():
        candidates.append(Path(DECISIONS_DIR) / supplied)
    return next((path for path in candidates if path.is_file()), None)


def _cmd_show(filename: str) -> int:
    path = _find_decision_file(filename)
    if path is None:
        print(f"Erro: arquivo de decisão não encontrado: {filename}", file=sys.stderr)
        return 1
    print(to_markdown(from_markdown(path)), end="")
    return 0


def _cmd_supersede(filename: str, replacement: str | None) -> int:
    replacement_name = Path(replacement).name if replacement else None
    path = _find_decision_file(filename)
    if path is None:
        print(f"Erro: arquivo de decisão não encontrado: {filename}", file=sys.stderr)
        return 1
    try:
        decision = from_markdown(path)
        if decision.status == DECISION_STATUS_SUBSTITUIDA:
            print(f"Erro: a decisão {path.name} já está substituída.", file=sys.stderr)
            return 1
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"Erro ao ler {path}: {exc}", file=sys.stderr)
        return 1

    lines = content.splitlines(keepends=True)
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if lines and lines[0].strip() == "---" and close is not None:
        found_status = False
        found_replacement = False
        for i in range(1, close):
            if re.match(r"^\s*status\s*:", lines[i]):
                lines[i] = re.sub(
                    r"^(\s*status\s*:\s*).*(\r?\n)?$",
                    rf"\g<1>{DECISION_STATUS_SUBSTITUIDA}\g<2>",
                    lines[i],
                )
                found_status = True
            elif replacement_name and re.match(r"^\s*substituida_por\s*:", lines[i]):
                lines[i] = re.sub(
                    r"^(\s*substituida_por\s*:\s*).*(\r?\n)?$",
                    rf"\g<1>{replacement_name}\g<2>",
                    lines[i],
                )
                found_replacement = True
        if not found_status:
            lines.insert(close, f"status: {DECISION_STATUS_SUBSTITUIDA}\n")
            close += 1
        if replacement_name and not found_replacement:
            lines.insert(close, f"substituida_por: {replacement_name}\n")
    else:
        lines = [
            "---\n",
            f"titulo: {decision.titulo}\n",
            f"data: {decision.data}\n",
            f"status: {DECISION_STATUS_SUBSTITUIDA}\n",
            f"tags: [{', '.join(decision.tags)}]\n",
        ]
        if replacement_name:
            lines.append(f"substituida_por: {replacement_name}\n")
        lines.extend(["---\n", "\n", content])
    try:
        path.write_text("".join(lines), encoding="utf-8")
    except OSError as exc:
        print(f"Erro ao atualizar {path}: {exc}", file=sys.stderr)
        return 1
    print(f"Decisão marcada como substituída: {path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Executa o parser e despacha o comando solicitado."""
    parser = argparse.ArgumentParser(
        prog="whylog",
        description="Guarda decisões técnicas de um projeto e responde perguntas sobre elas.",
    )
    parser.add_argument("--version", action="version", version=f"whylog {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Registrar uma nova decisão")
    add_parser.add_argument("--titulo")
    add_parser.add_argument("--decisao")
    add_parser.add_argument("--motivo")
    add_parser.add_argument("--alternativas", default="")
    add_parser.add_argument("--tags", default="")
    list_parser = subparsers.add_parser("list", help="Listar decisões registradas")
    list_parser.set_defaults(_unused=True)
    ask_parser = subparsers.add_parser("ask", help="Perguntar sobre decisões")
    ask_parser.add_argument("question", help="Pergunta sobre as decisões do projeto")
    show_parser = subparsers.add_parser("show", help="Exibir uma decisão")
    show_parser.add_argument("arquivo")
    supersede_parser = subparsers.add_parser("supersede", help="Marcar decisão como substituída")
    supersede_parser.add_argument("arquivo")
    supersede_parser.add_argument("--por", dest="replacement")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "add":
        fields = (args.titulo, args.decisao, args.motivo)
        if any(field is not None for field in fields) and not all(
            field is not None for field in fields
        ):
            parser.error("add requer --titulo, --decisao e --motivo em conjunto")
        return _cmd_add(args)
    if args.command == "list":
        return _cmd_list()
    if args.command == "ask":
        return _cmd_ask(args)
    if args.command == "show":
        return _cmd_show(args.arquivo)
    if args.command == "supersede":
        return _cmd_supersede(args.arquivo, args.replacement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
