"""Linha de comando: eweadn-x87 info | led | efeitos | sono | teclas | resetar-teclas."""

import argparse

from .i18n import tr
from .protocol import BRIGHT_MAX, EFFECTS, LAYOUT, SPEED_MAX, X87, describe_action


def main():
    ap = argparse.ArgumentParser(description=tr("Configura o teclado EWEADN X87 no Linux."))
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("info", help=tr("bateria, firmware e configuração atual"))
    l = sub.add_parser("led", help=tr("iluminação"))
    l.add_argument("--modo", "--mode", dest="modo", type=lambda x: int(x, 0),
                   help=tr("número do efeito (veja 'efeitos')"))
    l.add_argument("--cor", "--color", dest="cor", help=tr("cor em hex, ex.: ff0080"))
    l.add_argument("--colorido", "--rainbow", dest="colorido", choices=["sim", "nao", "yes", "no"])
    l.add_argument("--brilho", "--brightness", dest="brilho", type=int, help=tr("brilho de 1 a 5"))
    l.add_argument("--velocidade", "--speed", dest="velocidade", type=int, help=tr("velocidade de 1 a 5"))
    sub.add_parser("efeitos", aliases=["effects"], help=tr("lista os efeitos de luz"))
    s = sub.add_parser("sono", aliases=["sleep"], help=tr("tempo de sono em minutos (0 = desligado)"))
    s.add_argument("minutos", type=int, nargs="?")
    sub.add_parser("teclas", aliases=["keys"], help=tr("lista teclas remapeadas"))
    sub.add_parser("resetar-teclas", aliases=["reset-keys"],
                   help=tr("volta todas as teclas (normal e Fn) ao padrão"))
    a = ap.parse_args()
    cmd = {"effects": "efeitos", "sleep": "sono", "keys": "teclas", "reset-keys": "resetar-teclas"}.get(a.cmd, a.cmd)

    def minutes(m):
        return tr("{} min").format(m) if m else tr("desligado")

    if cmd == "efeitos":
        for v, n, *_ in EFFECTS:
            print(f"  {v:#04x}  {tr(n)}")
        return
    kb = X87()
    if cmd in (None, "info"):
        i, led = kb.info(), kb.led()
        names = {v: tr(n) for v, n, *_ in EFFECTS}
        print(tr("Conexão:   {}").format(f"{tr('2.4G (dongle)') if kb.wireless else tr('cabo')}  [{kb.path}]"))
        print(tr("Bateria:   {}%").format(i["battery"]))
        print(tr("Firmware:  {}").format(i["firmware"]))
        print(tr("Sono:      {}").format(minutes(kb.sleep_minutes())))
        print(tr("Luz:       {}, cor #{}, {}, brilho {}/{}, velocidade {}/{}").format(
            names.get(led["mode"], hex(led["mode"])), bytes(led["rgb"]).hex(),
            tr("colorido") if led["colorful"] else tr("cor única"),
            led["brightness"], BRIGHT_MAX, led["speed"], SPEED_MAX))
    elif cmd == "led":
        rgb = bytes.fromhex(a.cor) if a.cor else None
        col = None if a.colorido is None else a.colorido in ("sim", "yes")
        if rgb is not None and col is None:
            col = False
        kb.set_led(a.modo, rgb, col, a.brilho, a.velocidade)
        print("OK")
    elif cmd == "sono":
        if a.minutos is not None:
            kb.set_sleep_minutes(a.minutos)
        print(tr("Sono: {}").format(minutes(kb.sleep_minutes())))
    elif cmd == "teclas":
        for title, km, prefix in ((tr("Normal:"), kb.keymap(), ""), (tr("Com Fn:"), kb.fn_keymap(), "Fn+")):
            found = [(tr(label), describe_action(km[4 * idx:4 * idx + 4]))
                     for row in LAYOUT for idx, label, _ in row]
            found = [(l, d) for l, d in found if d]
            print(title)
            for label, d in found:
                print(f"  {prefix + label:>12} -> {d}")
            if not found:
                print(tr("  nada remapeado"))
    elif cmd == "resetar-teclas":
        kb.reset_keys()
        kb.reset_fn()
        print(tr("Teclas e camada Fn restauradas."))
    kb.close()
