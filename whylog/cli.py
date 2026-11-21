import argparse
import re
import subprocess
from pathlib import Path

from whylog import __version__
from whylog.decision import DECISIONS_DIR, create_decision, decision_filename, list_decisions, to_markdown
from whylog.llm import ask

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:[|][^]]*)?\]\]")


def _cmd_add() -> int:
    titulo = input("Título da decisão: ").strip()
    decisao = input("Decisão: ").strip()
    motivo = input("Motivo: ").strip()
    alternativas_input = input("Alternativas descartadas (separadas por vírgula): ")
    alternativas = [a.strip() for a in alternativas_input.split(",") if a.strip()]
    tags_input = input("Tags (separadas por vírgula, opcionais): ")
    tags = [t.strip() for t in tags_input.split(",") if t.strip()]

    nova_decisao = create_decision(
        titulo=titulo,
        decisao=decisao,
        motivo=motivo,
        alternativas=alternativas,
        tags=tags,
    )

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
        print(f"- [{d.status}] {d.arquivo} — {d.titulo} (tags: {tags})")
    return 0


def _decision_text(d) -> str:
    parts = [d.titulo, d.decisao, d.motivo, "\n".join(d.alternativas)]
    return "\n".join(str(p) for p in parts if str(p).strip())


def _git_log_recent(limit: int = 20) -> str:
    result = subprocess.run(
        ["git", "log", "--oneline", f"-{limit}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _build_context(decisions: list) -> str:
    blocks: list[str] = []
    used: set[str] = set()

    def add(d) -> None:
        key = Path(d.arquivo).name
        if key in used:
            return
        used.add(key)
        block = f"Arquivo: {d.arquivo}\nStatus: {d.status}"
        if d.tags:
            block += f"\nTags: {', '.join(d.tags)}"
        block += f"\nDecisão: {d.decisao}\nMotivo: {d.motivo}"
        if d.alternativas:
            block += "\nAlternativas descartadas: " + "; ".join(d.alternativas)
        blocks.append(block)
        for link in WIKILINK_RE.findall(_decision_text(d)):
            target_name = f"{link.strip()}.md"
            for other in decisions:
                if Path(other.arquivo).name == target_name:
                    add(other)
                    break

    for d in decisions:
        add(d)

    context = "\n\n".join(blocks)
    git_log = _git_log_recent()
    context += "\n\n## Git log recente\n" + (git_log if git_log else "(nenhum commit encontrado)")
    return context


def _cmd_ask(args) -> int:
    decisions = list_decisions(DECISIONS_DIR)
    if not decisions:
        print("Não encontrei nenhuma decisão registrada em decisions/ para responder.")
        return 0
    context = _build_context(decisions)
    try:
        answer = ask(args.question, context)
    except RuntimeError as e:
        print(f"Não foi possível consultar o modelo: {e}")
        return 0
    except Exception as e:
        print(f"Erro ao consultar o modelo: {e}")
        return 0
    print(answer)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="whylog",
        description="Guarda decisões técnicas de um projeto e responde perguntas sobre elas.",
    )
    parser.add_argument("--version", action="version", version=f"whylog {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Registrar uma nova decisão")
    list_parser = subparsers.add_parser("list", help="Listar decisões registradas")
    ask_parser = subparsers.add_parser("ask", help="Perguntar sobre decisões")
    ask_parser.add_argument("question", help="Pergunta sobre as decisões do projeto")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "add":
        return _cmd_add()
    if args.command == "list":
        return _cmd_list()
    if args.command == "ask":
        return _cmd_ask(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
