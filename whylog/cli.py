import argparse

from whylog import __version__


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="whylog",
        description="Guarda decisões técnicas de um projeto e responde perguntas sobre elas.",
    )
    parser.add_argument("--version", action="version", version=f"whylog {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("add", help="Registrar uma nova decisão")
    subparsers.add_parser("list", help="Listar decisões registradas")
    subparsers.add_parser("ask", help="Perguntar sobre decisões")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    print(f"Comando '{args.command}' ainda não implementado neste MVP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
