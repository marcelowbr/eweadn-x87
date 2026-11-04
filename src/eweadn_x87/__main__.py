"""Ponto de entrada: sem argumentos abre a interface; com argumentos usa a linha de comando."""

import sys


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--gapplication"):
        from .cli import main as cli_main
        from .i18n import tr
        from .protocol import X87Error

        try:
            cli_main()
        except X87Error as e:
            raise SystemExit(tr("Erro: {}").format(e))
        return 0
    from .gui import App

    return App().run(sys.argv[:1])


if __name__ == "__main__":
    sys.exit(main())
