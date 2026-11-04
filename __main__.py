"""Ponto de entrada: sem argumentos abre a interface; com argumentos usa a linha de comando."""

import sys


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--gapplication"):
        import x87proto

        try:
            x87proto._cli()
        except x87proto.X87Error as e:
            raise SystemExit(x87proto.tr("Erro: {}").format(e))
        return 0
    import x87gui

    return x87gui.App().run(sys.argv[:1])


if __name__ == "__main__":
    sys.exit(main())
