#!/usr/bin/env python3
"""Interface GTK4/libadwaita para o teclado EWEADN X87."""

import json
import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, GObject, Gio, Gtk  # noqa: E402

from . import i18n  # noqa: E402
from . import protocol as p  # noqa: E402
from .i18n import tr  # noqa: E402
from .preview import KeyboardPreview  # noqa: E402

UNIT = 54  # pixels por unidade de tecla (1u)
GAP = 4

CONFIG = i18n.CONFIG

# Cores do teclado desenhado, uma paleta por tema
PALETTE_LIGHT = b"""
@define-color case_bg #d5d9e0;
@define-color case_edge #b8bec9;
@define-color key_bg #fbfbfc;
@define-color key_hover #ffffff;
@define-color key_edge #b3b9c4;
@define-color key_fg #1d2026;
@define-color key_dim #6b7280;
@define-color fn_mark #e66100;
"""
PALETTE_DARK = b"""
@define-color case_bg #141519;
@define-color case_edge #070809;
@define-color key_bg #2c2e35;
@define-color key_hover #363944;
@define-color key_edge #0d0e11;
@define-color key_fg #e9eaee;
@define-color key_dim #9aa0ab;
@define-color fn_mark #ffa348;
"""

CSS = b"""
.keyboard-case {
  padding: 16px; border-radius: 18px;
  background: @case_bg;
  border: 1px solid @case_edge;
  box-shadow: 0 10px 30px -12px alpha(black, 0.45), inset 0 1px alpha(white, 0.06);
}
.key {
  min-width: 0; min-height: 0; padding: 3px 4px; border-radius: 8px;
  background: @key_bg; color: @key_fg;
  border: 1px solid @key_edge; border-bottom-width: 4px;
  box-shadow: inset 0 1px alpha(white, 0.10);
  transition: background 120ms, border-color 120ms;
}
.key:hover { background: @key_hover; border-color: @accent_bg_color; }
.key:active { border-bottom-width: 2px; padding-top: 5px; }
.key:disabled { opacity: 0.45; }
.key .key-name { font-size: 0.85em; font-weight: 700; }
.key .key-shift { font-size: 0.72em; color: @key_dim; margin-bottom: -3px; }
.key .key-map { font-size: 0.68em; font-weight: 600; }
.key .key-fn {
  font-size: 0.66em; font-weight: 700; color: @fn_mark;
}
.key.remapped {
  background: @accent_bg_color; color: @accent_fg_color;
  border-color: shade(@accent_bg_color, 0.7);
}
.key.remapped .key-shift { color: alpha(@accent_fg_color, 0.75); }
.key.remapped .key-fn { color: @accent_fg_color; }
.key.has-fn { border-bottom-color: @fn_mark; }
.swatch { min-width: 18px; min-height: 14px; border-radius: 4px; }
.swatch.remapped { background: @accent_bg_color; }
.swatch.has-fn { background: @key_bg; border: 1px solid @key_edge; border-bottom: 4px solid @fn_mark; }

.hero { padding: 28px 24px; }
.battery-big { font-size: 3.2em; font-weight: 800; }
.battery-icon { color: @accent_color; }
.battery-icon.low { color: @error_color; }
.battery-icon.mid { color: @warning_color; }
.battery-icon.high { color: @success_color; }
progressbar.battery trough { min-height: 10px; border-radius: 99px; }
progressbar.battery progress { min-height: 10px; border-radius: 99px; }
.status-pill {
  padding: 4px 12px; border-radius: 99px; font-weight: 600; font-size: 0.9em;
  background: alpha(@success_color, 0.15); color: @success_color;
}
.status-pill.off { background: alpha(@error_color, 0.15); color: @error_color; }

.capture { padding: 16px; border-radius: 12px; border: 2px dashed alpha(@accent_color, 0.6); }
.capture:focus { background: alpha(@accent_bg_color, 0.08); }
.capture-title { font-size: 1.15em; font-weight: bold; }
.layer-btn { padding: 6px 10px; }
.layer-btn .layer-cur { font-size: 0.8em; opacity: 0.8; }
"""


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        with open(CONFIG, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass

# Geometria TKL ANSI: índice da tecla -> (x, y, largura) em unidades
_W = {92: 2, 32: 1.5, 60: 1.5, 48: 1.75, 76: 2.25, 64: 2.25, 75: 2.75, 83: 6.25,
      80: 1.25, 81: 1.25, 82: 1.25, 84: 1.25, 85: 1.25, 86: 1.25, 87: 1.25}
_ROW_Y = [0, 1.35, 2.35, 3.35, 4.35, 5.35]
_X_OVERRIDE = {
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6.5, 6: 7.5, 7: 8.5, 8: 9.5, 9: 11, 10: 12, 11: 13, 12: 14,
    99: 15.25, 100: 16.25, 102: 17.25, 103: 15.25, 104: 16.25, 105: 17.25,
    106: 15.25, 107: 16.25, 108: 17.25, 90: 16.25, 88: 15.25, 89: 16.25, 91: 17.25,
}


def tkl_geometry():
    geo = {}
    for r, row in enumerate(p.LAYOUT):
        x = 0.0
        for idx, _, _ in row:
            if idx in _X_OVERRIDE:
                x = _X_OVERRIDE[idx]
            w = _W.get(idx, 1)
            geo[idx] = (x, _ROW_Y[r], w)
            x += w
    return geo


NAV = {"↑", "↓", "←", "→", "Ins", "Home", "PgUp", "Del", "End", "PgDn", "PrtSc", "ScrLk", "Pause",
       "Esc", "Tab", "Caps", "Enter", "Backspace", "Espaço"}


DEAD = {"dead_acute": "´", "dead_grave": "`", "dead_tilde": "~", "dead_perispomeni": "~",
        "dead_circumflex": "^", "dead_diaeresis": "¨", "dead_cedilla": "¸"}


def typed_chars(hid):
    """O que a tecla digita no layout atual do sistema: (sozinha, com Shift)."""
    ev = p.HID_TO_EVDEV.get(hid)
    display = Gdk.Display.get_default()
    if ev is None or display is None:
        return None, None
    ok, keys, vals = display.map_keycode(ev + 8)
    out = [None, None]
    for k, v in zip(keys or [], vals or []):
        if ok and k.group == 0 and k.level in (0, 1) and out[k.level] is None:
            uni = Gdk.keyval_to_unicode(v)
            ch = DEAD.get(Gdk.keyval_name(v) or "") or (chr(uni) if uni else None)
            if ch and ch.isprintable() and not ch.isspace():
                out[k.level] = ch
    return out[0], out[1]


def typed_label(hid):
    base, shift = typed_chars(hid)
    if not base:
        return None
    return base.upper() if base.isalpha() and shift == base.upper() else base


def describe(action):
    """Descrição da ação usando o caractere real do layout do sistema."""
    a = bytes(action)
    if a[:1] == b"\x02" and a[1] == 0 and (t := typed_label(a[2])):
        return t
    return p.describe_action(a)


def target_groups():
    """Opções do seletor: [(título, [(nome, detalhe, ação de 4 bytes)])]."""
    letters, nav, fkeys = [], [], []
    seen = set()
    for row in p.LAYOUT:
        for _, label, code in row:
            if not code or code in seen or code in p.MODIFIERS:
                continue
            seen.add(code)
            if label in NAV:
                nav.append((label, code))
            elif label.startswith("F") and label[1:].isdigit():
                fkeys.append((label, "", p.action_keyboard(code)))
            else:
                letters.append(code)
    letters += [0x64, 0x87]

    chars = []
    for code in letters:
        base, shift = typed_chars(code)
        name = typed_label(code) or p.key_name(code)
        if code in p.EXTRA_KEYS and not typed_label(code):
            name = tr(p.EXTRA_KEYS[code])
        if code in p.EXTRA_KEYS:
            detail = tr("não existe no X87, só no ABNT2")
        else:
            detail = tr("tecla física {}").format(p.key_name(code))
        if shift and shift != name:
            detail = tr("com Shift: {}   ·   {}").format(shift, detail)
        chars.append((name, detail, p.action_keyboard(code)))

    fkeys += [(n, "", p.action_keyboard(c)) for c, n in p.EXTRA_KEYS.items() if n.startswith("F")]
    order = ["↑", "↓", "←", "→", "Home", "End", "PgUp", "PgDn", "Ins", "Del", "Esc", "Enter",
             "Backspace", "Tab", "Espaço", "Caps", "PrtSc", "ScrLk", "Pause"]
    nav.sort(key=lambda it: order.index(it[0]) if it[0] in order else len(order))
    arrows = {"↑": "↑  Seta para cima", "↓": "↓  Seta para baixo",
              "←": "←  Seta para a esquerda", "→": "→  Seta para a direita"}
    nav = [(tr(arrows[l]) if l in arrows else (f"{p.ICONS[c]} {tr(l)}" if c in p.ICONS else tr(l)), "",
            p.action_keyboard(c))
           for l, c in nav]
    numpad = [(n, "", p.action_keyboard(c)) for c, n in p.EXTRA_KEYS.items() if n.startswith("Num")]
    return [
        (tr("Setas e navegação"), nav),
        (tr("Letras, números e símbolos"), chars),
        (tr("Teclas F"), fkeys),
        (tr("Modificadores"), [(tr(n), "", p.action_keyboard(c)) for c, n in p.MODIFIERS.items()]),
        (tr("Mídia e sistema"), [(tr(n), "", p.action_media(u)) for u, n in p.MEDIA]),
        ("Mouse", [(tr(n), "", p.action_mouse(k, v)) for (k, v), n in p.MOUSE]),
        (tr("Teclado numérico"), numpad),
    ]


NORMAL, FN = p.CMD_KEYS, p.CMD_FN  # as duas camadas, identificadas pelo comando de leitura


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="EWEADN X87", default_width=1100, default_height=640)
        self.kb = None
        self.kb_lock = threading.Lock()
        self.maps = {NORMAL: bytearray(512), FN: bytearray(512)}
        self.loading = False
        self._led_timer = 0
        self.key_buttons = {}

        self.toast = Adw.ToastOverlay()
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(self._page_status(), "status", tr("Status"), "battery-good-symbolic")
        stack.add_titled_with_icon(self._page_light(), "light", tr("Iluminação"), "display-brightness-symbolic")
        stack.add_titled_with_icon(self._page_keys(), "keys", tr("Teclas"), "input-keyboard-symbolic")
        stack.add_titled_with_icon(self._page_settings(), "settings", tr("Ajustes"), "preferences-system-symbolic")

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE))
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=tr("Ler do teclado"))
        refresh.connect("clicked", lambda *_: self.reload())
        header.pack_start(refresh)

        menu = Gio.Menu()
        theme = Gio.Menu()
        theme.append(tr("Seguir o sistema"), "app.theme::system")
        theme.append(tr("Claro"), "app.theme::light")
        theme.append(tr("Escuro"), "app.theme::dark")
        menu.append_section(tr("Aparência"), theme)
        lang = Gio.Menu()
        lang.append(tr("Automático"), "app.lang::auto")
        lang.append("Português", "app.lang::pt")
        lang.append("English", "app.lang::en")
        menu.append_section(tr("Idioma"), lang)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       tooltip_text=tr("Menu"), primary=True))

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        self.toast.set_child(stack)
        view.set_content(self.toast)
        self.set_content(view)

        self.reload()
        self._battery_timer = GLib.timeout_add_seconds(30, self._poll_battery)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_):
        GLib.source_remove(self._battery_timer)
        with self.kb_lock:
            if self.kb:
                self.kb.close()
                self.kb = None

    # ---------- utilidades ----------
    def notify(self, msg):
        self.toast.add_toast(Adw.Toast(title=msg, timeout=3))

    def run_bg(self, fn, done=None, ok_msg=None):
        def work():
            try:
                with self.kb_lock:
                    if self.kb is None:
                        self.kb = p.X87()
                    kb = self.kb
                res = fn(kb)
                GLib.idle_add(self._bg_ok, done, res, ok_msg)
            except (p.X87Error, OSError) as e:
                with self.kb_lock:
                    if self.kb:
                        try:
                            self.kb.close()
                        except OSError:
                            pass
                    self.kb = None
                GLib.idle_add(self._bg_err, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _bg_ok(self, done, res, ok_msg):
        if done:
            done(res)
        if ok_msg:
            self.notify(ok_msg)

    def _bg_err(self, msg):
        self.conn_row.set_subtitle(tr("Desconectado"))
        self.pill.set_label(tr("Desconectado"))
        self.pill.set_css_classes(["status-pill", "off"])
        self.notify(msg)

    # ---------- páginas ----------
    def _page_status(self):
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup()
        hero = Gtk.Box(spacing=24, css_classes=["card", "hero"])
        self.bat_icon = Gtk.Image(icon_name="battery-missing-symbolic", pixel_size=72,
                                  css_classes=["battery-icon"], valign=Gtk.Align.CENTER)
        hero.append(self.bat_icon)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True,
                      valign=Gtk.Align.CENTER)
        top = Gtk.Box(spacing=12)
        top.append(Gtk.Label(label="EWEADN X87", css_classes=["title-2"], xalign=0, hexpand=True))
        self.pill = Gtk.Label(label=tr("Conectando…"), css_classes=["status-pill"], valign=Gtk.Align.CENTER)
        top.append(self.pill)
        col.append(top)
        self.bat_label = Gtk.Label(label="--%", css_classes=["battery-big"], xalign=0)
        col.append(self.bat_label)
        self.bat_bar = Gtk.ProgressBar(hexpand=True, css_classes=["battery"])
        col.append(self.bat_bar)
        col.append(Gtk.Label(label=tr("Atualiza a cada 30 segundos"), css_classes=["dim-label", "caption"], xalign=0))
        hero.append(col)
        g.add(hero)
        page.add(g)

        info = Adw.PreferencesGroup(title=tr("Aparelho"))
        self.conn_row = Adw.ActionRow(title=tr("Conexão"), subtitle="—")
        self.conn_row.add_prefix(Gtk.Image(icon_name="network-wireless-symbolic"))
        self.fw_row = Adw.ActionRow(title="Firmware", subtitle="—")
        self.fw_row.add_prefix(Gtk.Image(icon_name="application-x-firmware-symbolic"))
        info.add(self.conn_row)
        info.add(self.fw_row)
        page.add(info)
        return page

    def _page_light(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                        margin_top=16, margin_bottom=24, margin_start=16, margin_end=16)

        labels = {}
        for row in p.LAYOUT:
            for idx, label, code in row:
                labels[idx] = p.ICONS.get(code, tr(label)) if len(label) > 3 else tr(label)
        self.preview = KeyboardPreview(tkl_geometry(), labels)
        self.preview.set_size_request(-1, 300)
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.append(self.preview)
        frame.append(Gtk.Label(label=tr("Pré-visualização aproximada. Nos efeitos que reagem às teclas, "
                                        "digite com o app em foco para ver."),
                               css_classes=["dim-label", "caption"]))
        outer.append(frame)

        g = Adw.PreferencesGroup(title=tr("Efeito"), hexpand=True)
        self.effect_row = Adw.ComboRow(title=tr("Efeito"),
                                       model=Gtk.StringList.new([tr(e[1]) for e in p.EFFECTS]))
        self.colorful_row = Adw.SwitchRow(title=tr("Colorido (arco-íris)"),
                                          subtitle=tr("Desligado usa a cor escolhida abaixo"))
        self.color_btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),
                                               valign=Gtk.Align.CENTER)
        self.color_row = Adw.ActionRow(title=tr("Cor"))
        self.color_row.add_suffix(self.color_btn)
        for w in (self.effect_row, self.colorful_row, self.color_row):
            g.add(w)

        g2 = Adw.PreferencesGroup(title=tr("Ajustes do efeito"), hexpand=True)
        self.bright_row = Adw.SpinRow.new_with_range(1, p.BRIGHT_MAX, 1)
        self.bright_row.set_title(tr("Brilho"))
        self.speed_row = Adw.SpinRow.new_with_range(1, p.SPEED_MAX, 1)
        self.speed_row.set_title(tr("Velocidade"))
        self.dir_row = Adw.SwitchRow(title=tr("Inverter direção"))
        for w in (self.bright_row, self.speed_row, self.dir_row):
            g2.add(w)

        cols = Gtk.Box(spacing=24, homogeneous=True)
        cols.append(g)
        cols.append(g2)
        clamp = Adw.Clamp(maximum_size=1000, child=cols)
        outer.append(clamp)

        self.effect_row.connect("notify::selected", self._on_led_changed)
        self.colorful_row.connect("notify::active", self._on_led_changed)
        self.color_btn.connect("notify::rgba", self._on_led_changed)
        self.bright_row.connect("notify::value", self._on_led_changed)
        self.speed_row.connect("notify::value", self._on_led_changed)
        self.dir_row.connect("notify::active", self._on_led_changed)

        # teclas reais acionam os efeitos reativos da prévia
        keyctl = Gtk.EventControllerKey()
        keyctl.connect("key-pressed", self._on_preview_key)
        self.add_controller(keyctl)
        return Gtk.ScrolledWindow(child=outer)

    def _on_preview_key(self, _ctl, _keyval, keycode, _state):
        hid = p.EVDEV_TO_HID.get(keycode - 8)
        idx = next((i for row in p.LAYOUT for i, _, c in row if c == hid and c), None)
        if idx is not None:
            self.preview.press(idx)
        return False

    def _led_args(self):
        c = self.color_btn.get_rgba()
        return dict(
            mode=p.EFFECTS[self.effect_row.get_selected()][0],
            rgb=(round(c.red * 255), round(c.green * 255), round(c.blue * 255)),
            colorful=self.colorful_row.get_active(),
            brightness=int(self.bright_row.get_value()),
            speed=int(self.speed_row.get_value()),
            direction=1 if self.dir_row.get_active() else 0,
        )

    def _page_keys(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                        margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)

        # barra superior: dica + legenda + restaurar (sempre visível)
        top = Gtk.Box(spacing=12)
        hint = Gtk.Label(label=tr("Clique numa tecla para mudar o que ela faz, sozinha ou com Fn."),
                         xalign=0, hexpand=True, wrap=True, css_classes=["dim-label"])
        top.append(hint)
        legend = Gtk.Box(spacing=12)
        for css, text in (("remapped", "remapeada"), ("has-fn", "tem função Fn")):
            sw = Gtk.Box(css_classes=["swatch", css], valign=Gtk.Align.CENTER)
            item = Gtk.Box(spacing=6)
            item.append(sw)
            item.append(Gtk.Label(label=tr(text), css_classes=["dim-label"]))
            legend.append(item)
        top.append(legend)

        menu = Gio.Menu()
        menu.append(tr("Restaurar teclas normais"), "win.reset-normal")
        menu.append(tr("Restaurar funções Fn"), "win.reset-fn")
        menu.append(tr("Restaurar tudo"), "win.reset-all")
        for name, layers in (("reset-normal", (NORMAL,)), ("reset-fn", (FN,)), ("reset-all", (NORMAL, FN))):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda *_a, ls=layers: self._reset_layers(ls))
            self.add_action(act)
        top.append(Gtk.MenuButton(label=tr("Restaurar"),
                                  menu_model=menu, always_show_arrow=True))
        outer.append(top)

        # teclado TKL em posições reais
        fixed = Gtk.Fixed()
        keys = {i: (l, c) for row in p.LAYOUT for i, l, c in row}
        for idx, (x, y, w) in tkl_geometry().items():
            label, code = keys[idx]
            label = tr(label)
            if code in p.ICONS:
                label = f"{p.ICONS[code]} {label}" if w > 1.25 else p.ICONS[code]
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
            if code in p.SHIFTED:
                inner.append(Gtk.Label(label=p.SHIFTED[code], css_classes=["key-shift"]))
            name = Gtk.Label(label=label, css_classes=["key-name"], ellipsize=3)
            mapped = Gtk.Label(css_classes=["key-map"], ellipsize=3, visible=False)
            fnlbl = Gtk.Label(css_classes=["key-fn"], ellipsize=3, visible=False)
            for wdg in (name, mapped, fnlbl):
                inner.append(wdg)
            b = Gtk.Button(child=inner, css_classes=["key"])
            b.set_size_request(int(w * UNIT) - GAP, UNIT - GAP)
            if idx == p.FN_INDEX:
                b.set_sensitive(False)
                b.set_tooltip_text(tr("Tecla Fn"))
            b.connect("clicked", self._on_key_clicked, idx)
            fixed.put(b, x * UNIT, y * UNIT)
            self.key_buttons[idx] = (b, mapped, fnlbl)
        case = Gtk.Box(css_classes=["keyboard-case"], halign=Gtk.Align.CENTER)
        case.append(fixed)
        outer.append(case)
        return Gtk.ScrolledWindow(child=outer)

    def _page_settings(self):
        page = Adw.PreferencesPage()
        g = Adw.PreferencesGroup(
            title=tr("Modo de sono"),
            description=tr("Minutos sem uso até o teclado dormir. "
                           "Desligar pode evitar que a conexão 2.4G caia, mas gasta mais bateria."))
        self.sleep_switch = Adw.SwitchRow(title=tr("Ativar modo de sono"))
        self.sleep_spin = Adw.SpinRow.new_with_range(1, 30, 1)
        self.sleep_spin.set_title(tr("Minutos"))
        apply = Gtk.Button(label=tr("Aplicar"), valign=Gtk.Align.CENTER, css_classes=["suggested-action"])
        apply.connect("clicked", self._on_sleep_apply)
        row = Adw.ActionRow(title=tr("Gravar no teclado"))
        row.add_suffix(apply)
        self.sleep_switch.bind_property("active", self.sleep_spin, "sensitive",
                                        GObject.BindingFlags.SYNC_CREATE)
        for w in (self.sleep_switch, self.sleep_spin, row):
            g.add(w)
        page.add(g)
        return page

    # ---------- leitura ----------
    def reload(self):
        def fetch(kb):
            return (kb.info(), kb.led(), kb.keymap(), kb.fn_keymap(), kb.sleep_minutes(),
                    kb.wireless, kb.path)

        self.run_bg(fetch, self._apply_state)

    def _apply_state(self, res):
        info, led, keymap, fnmap, sleep, wireless, path = res
        self.loading = True
        self._show_battery(info)
        self.conn_row.set_subtitle(f"{tr('Sem fio 2.4G (dongle)') if wireless else tr('Cabo USB')} · {path}")
        self.fw_row.set_subtitle(info["firmware"])

        modes = [e[0] for e in p.EFFECTS]
        if led["mode"] in modes:
            self.effect_row.set_selected(modes.index(led["mode"]))
        self.colorful_row.set_active(led["colorful"])
        c = Gdk.RGBA()
        c.parse("#%02x%02x%02x" % led["rgb"])
        self.color_btn.set_rgba(c)
        self.bright_row.set_value(max(1, led["brightness"]))
        self.speed_row.set_value(max(1, led["speed"]))
        self.dir_row.set_active(bool(led["direction"]))
        self._update_led_sensitivity()

        self.sleep_spin.get_adjustment().set_upper(max(30, sleep))
        self.sleep_switch.set_active(sleep > 0)
        if sleep:
            self.sleep_spin.set_value(sleep)

        self.maps = {NORMAL: bytearray(keymap), FN: bytearray(fnmap)}
        self._refresh_keys()
        self.loading = False

    def _show_battery(self, info):
        pct = max(0, min(100, info["battery"]))
        self.bat_label.set_label(f"{pct}%")
        self.bat_bar.set_fraction(pct / 100)
        self.bat_icon.set_from_icon_name(f"battery-level-{pct // 10 * 10}-symbolic")
        level = "low" if pct < 20 else "mid" if pct < 50 else "high"
        self.bat_icon.set_css_classes(["battery-icon", level])
        self.pill.set_label(tr("Conectado"))
        self.pill.set_css_classes(["status-pill"])

    def _poll_battery(self):
        if self.kb is not None:
            self.run_bg(lambda kb: kb.info(), self._show_battery)
        return True

    # ---------- iluminação ----------
    def _update_led_sensitivity(self):
        _, _, has_speed, has_dir, has_color = p.EFFECTS[self.effect_row.get_selected()]
        off = self.effect_row.get_selected() == 0
        self.colorful_row.set_sensitive(has_color)
        self.color_row.set_sensitive(has_color and not self.colorful_row.get_active())
        self.bright_row.set_sensitive(not off)
        self.speed_row.set_sensitive(has_speed)
        self.dir_row.set_sensitive(has_dir)

    def _on_led_changed(self, *_):
        self._update_led_sensitivity()
        self.preview.configure(**self._led_args())
        if self.loading:
            return
        if self._led_timer:
            GLib.source_remove(self._led_timer)
        self._led_timer = GLib.timeout_add(350, self._send_led)

    def _send_led(self):
        self._led_timer = 0
        args = self._led_args()
        self.run_bg(lambda kb: kb.set_led(**args))
        return False

    # ---------- teclas ----------
    def _label(self, idx):
        label, code = next((l, c) for row in p.LAYOUT for i, l, c in row if i == idx)
        return f"{label} {p.SHIFTED[code]}" if code in p.SHIFTED else tr(label)

    def _action(self, layer, idx):
        return describe(self.maps[layer][4 * idx:4 * idx + 4])

    def _refresh_keys(self):
        for idx, (b, mapped, fnlbl) in self.key_buttons.items():
            normal = self._action(NORMAL, idx)
            fn = None if idx in p.FN_LOCKED else self._action(FN, idx)
            b.set_css_classes([c for c in b.get_css_classes() if c not in ("remapped", "has-fn")])
            if normal:
                b.add_css_class("remapped")
            if fn:
                b.add_css_class("has-fn")
            mapped.set_label(f"→ {normal}" if normal else "")
            mapped.set_visible(bool(normal))
            fnlbl.set_label(f"Fn: {fn}" if fn else "")
            fnlbl.set_visible(bool(fn))
            code = next(c for row in p.LAYOUT for i, _, c in row if i == idx)
            base, shift = typed_chars(code)
            typed = (tr("No seu layout digita: {}").format(base)
                     + (tr("  (Shift: {})").format(shift) if shift else "")) if base else None
            tips = [typed, f"{self._label(idx)} → {normal}" if normal else None,
                    f"Fn + {self._label(idx)} → {fn}" if fn else None]
            b.set_tooltip_text("\n".join(t for t in tips if t) or None)

    def _on_key_clicked(self, _btn, idx):
        label = self._label(idx)
        fn_locked = idx in p.FN_LOCKED
        dlg = Adw.Dialog(title=tr("Tecla {}").format(label), content_width=440, content_height=640)
        state = {"layer": NORMAL}
        page = Adw.PreferencesPage()

        # escolha da combinação: tecla sozinha ou Fn + tecla
        def layer_button(text, layer):
            cur = self._action(layer, idx) or (tr("função de fábrica") if layer == FN else tr("padrão"))
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.append(Gtk.Label(label=text, css_classes=["heading"]))
            box.append(Gtk.Label(label=tr("atual: {}").format(cur), css_classes=["layer-cur"], ellipsize=3))
            return Gtk.ToggleButton(child=box, css_classes=["layer-btn"], hexpand=True)

        b_norm = layer_button(tr("Ao apertar {}").format(label), NORMAL)
        b_fn = layer_button(tr("Ao apertar Fn + {}").format(label), FN)
        b_norm.set_active(True)
        b_fn.set_group(b_norm)
        if fn_locked:
            b_fn.set_sensitive(False)
            b_fn.set_tooltip_text(tr("Fn + F1…F12 são funções de fábrica"))
        layers = Gtk.Box(css_classes=["linked"])
        layers.append(b_norm)
        layers.append(b_fn)
        lg = Adw.PreferencesGroup()
        lg.add(layers)
        page.add(lg)

        # captura: aperta a tecla desejada
        cap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, css_classes=["capture"], focusable=True)
        cap_title = Gtk.Label(css_classes=["capture-title"])
        cap.append(cap_title)
        cap.append(Gtk.Label(label=tr("ou escolha na lista abaixo"), css_classes=["dim-label"]))
        cg = Adw.PreferencesGroup()
        cg.add(cap)
        page.add(cg)

        default_row = Adw.ActionRow(activatable=True)
        default_row.add_prefix(Gtk.Image(icon_name="edit-undo-symbolic"))

        def on_layer(*_):
            state["layer"] = NORMAL if b_norm.get_active() else FN
            combo = f"Fn + {label}" if state["layer"] == FN else label
            cap_title.set_label(tr("Aperte a tecla que {} deve virar").format(combo))
            default_row.set_title(tr("Voltar à função de fábrica") if state["layer"] == FN else tr("Voltar ao padrão"))
            cap.grab_focus()

        b_norm.connect("toggled", on_layer)
        on_layer()

        keyctl = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keyctl.connect("key-pressed", self._on_capture_key, dlg, idx, state)
        dlg.add_controller(keyctl)

        search = Gtk.SearchEntry(placeholder_text=tr("Buscar função…"))
        sg = Adw.PreferencesGroup()
        sg.add(search)
        page.add(sg)

        dg = Adw.PreferencesGroup()
        default_row.connect("activated", lambda *_: self._assign(dlg, idx, state["layer"], tr("padrão"), bytes(4)))
        dg.add(default_row)
        page.add(dg)

        rows = []
        for gtitle, items in target_groups():
            g = Adw.PreferencesGroup(title=gtitle)
            for name, detail, action in items:
                r = Adw.ActionRow(activatable=True, use_markup=False)
                r.set_title(name)
                r.set_subtitle(detail)
                r.connect("activated",
                          lambda _r, n=name, a=action: self._assign(dlg, idx, state["layer"], n, a))
                g.add(r)
                rows.append((f"{name} {detail}".lower(), r, g))
            page.add(g)

        def on_search(entry):
            q = entry.get_text().lower()
            for n, r, _ in rows:
                r.set_visible(q in n)
            for g in {g for *_, g in rows}:
                g.set_visible(any(r.get_visible() for _, r, gg in rows if gg is g))

        search.connect("search-changed", on_search)
        tv = Adw.ToolbarView(content=page)
        tv.add_top_bar(Adw.HeaderBar())
        dlg.set_child(tv)
        dlg.present(self)
        cap.grab_focus()

    def _on_capture_key(self, _ctl, _keyval, keycode, _state, dlg, idx, state):
        focus = dlg.get_focus()
        if not (focus and focus.has_css_class("capture")):
            return False  # foco na busca, na lista ou nos botões
        hid = p.EVDEV_TO_HID.get(keycode - 8)
        if hid is None:
            self.notify(tr("Essa tecla não pode ser capturada, escolha na lista"))
            return True
        self._assign(dlg, idx, state["layer"], describe(p.action_keyboard(hid)), p.action_keyboard(hid))
        return True

    def _assign(self, dlg, idx, layer, name, action):
        dlg.close()
        combo = f"Fn + {self._label(idx)}" if layer == FN else self._label(idx)

        def work(kb):
            # lê o estado atual do teclado para não sobrescrever outras teclas
            km = kb.read(layer, 512)
            km[4 * idx:4 * idx + 4] = action
            kb.write(layer + p.WRITE, km)
            return kb.read(layer, 512)

        def done(km):
            self.maps[layer] = bytearray(km)
            self._refresh_keys()

        self.run_bg(work, done, f"{combo} → {name}")

    def _reset_layers(self, layers):
        def work(kb):
            for layer in layers:
                kb.write(layer + p.WRITE, bytes(512))

        def done(_):
            for layer in layers:
                self.maps[layer] = bytearray(512)
            self._refresh_keys()

        self.run_bg(work, done, tr("Teclas restauradas"))

    # ---------- ajustes ----------
    def _on_sleep_apply(self, *_):
        minutes = int(self.sleep_spin.get_value()) if self.sleep_switch.get_active() else 0
        msg = tr("Sono: {} min").format(minutes) if minutes else tr("Modo de sono desligado")
        self.run_bg(lambda kb: kb.set_sleep_minutes(minutes), ok_msg=msg)


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.eweadn.x87")

    def do_startup(self):
        Adw.Application.do_startup(self)
        display = Gdk.Display.get_default()
        self.palette = Gtk.CssProvider()
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        for prov, prio in ((self.palette, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION),
                           (css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)):
            Gtk.StyleContext.add_provider_for_display(display, prov, prio)

        self.cfg = load_config()
        sm = Adw.StyleManager.get_default()
        sm.connect("notify::dark", lambda *_: self._apply_palette())
        theme = self.cfg.get("theme", "system")
        act = Gio.SimpleAction.new_stateful("theme", GLib.VariantType.new("s"), GLib.Variant("s", theme))
        act.connect("activate", self._on_theme)
        self.add_action(act)
        self._set_scheme(theme)
        self._apply_palette()

        lang = self.cfg.get("lang", "auto")
        act = Gio.SimpleAction.new_stateful("lang", GLib.VariantType.new("s"), GLib.Variant("s", lang))
        act.connect("activate", self._on_lang)
        self.add_action(act)

    def _on_lang(self, act, value):
        if value.get_string() == act.get_state().get_string():
            return
        act.set_state(value)
        self.cfg["lang"] = value.get_string()
        save_config(self.cfg)
        i18n.set_language(value.get_string())
        # recria a janela com os textos no novo idioma
        old = self.props.active_window
        win = Window(self)
        if old:
            win.set_default_size(old.get_width(), old.get_height())
            old.destroy()
        win.present()

    def _on_theme(self, act, value):
        act.set_state(value)
        self._set_scheme(value.get_string())
        self.cfg["theme"] = value.get_string()
        save_config(self.cfg)

    def _set_scheme(self, theme):
        Adw.StyleManager.get_default().set_color_scheme({
            "light": Adw.ColorScheme.FORCE_LIGHT,
            "dark": Adw.ColorScheme.FORCE_DARK,
        }.get(theme, Adw.ColorScheme.DEFAULT))

    def _apply_palette(self):
        dark = Adw.StyleManager.get_default().get_dark()
        self.palette.load_from_data(PALETTE_DARK if dark else PALETTE_LIGHT)

    def do_activate(self):
        (self.props.active_window or Window(self)).present()
