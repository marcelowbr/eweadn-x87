"""Pré-visualização animada dos efeitos de luz do X87 (aproximação do firmware)."""

import colorsys
import math
import random

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, GLib, Graphene, Gsk, Gtk, Pango  # noqa: E402

TOTAL_W, TOTAL_H = 18.25, 6.35
REACTIVE = {0x02, 0x03, 0x0D, 0x0E, 0x0F}


class Key:
    __slots__ = ("idx", "label", "x", "y", "w", "nx", "ny", "col", "row", "phase", "hue")

    def __init__(self, idx, label, x, y, w, rnd):
        self.idx, self.label, self.x, self.y, self.w = idx, label, x, y, w
        self.nx = (x + w / 2) / TOTAL_W
        self.ny = (y + 0.5) / TOTAL_H
        self.col = int(x + w / 2)
        self.row = round(y)
        self.phase = rnd.random()
        self.hue = rnd.random()


def hsv(h):
    return colorsys.hsv_to_rgb(h % 1.0, 1.0, 1.0)


def rrect(x, y, w, h, r):
    rect = Graphene.Rect()
    rect.init(x, y, w, h)
    rr = Gsk.RoundedRect()
    rr.init_from_rect(rect, r)  # o valor de retorno vem corrompido no PyGObject; usar o objeto
    return rr


def rgba(r, g, b, a=1.0):
    c = Gdk.RGBA()
    c.red, c.green, c.blue, c.alpha = r, g, b, a
    return c


class KeyboardPreview(Gtk.Widget):
    def __init__(self, geometry, labels):
        super().__init__(hexpand=True)
        rnd = random.Random(87)
        self.keys = [Key(i, labels[i], x, y, w, rnd) for i, (x, y, w) in geometry.items()]
        self.by_idx = {k.idx: k for k in self.keys}
        self.col_seed = {c: rnd.random() for c in range(20)}
        self.mode, self.rgb, self.colorful = 0x01, (1.0, 1.0, 1.0), False
        self.brightness, self.speed, self.direction = 5, 3, 0
        self.presses = []  # (tecla, instante)
        self.t = 0.0
        self._last_frame = None
        self._last_real = -10.0
        self._next_fake = 0.0
        self._layouts = {}
        self._font_px = None
        self.add_tick_callback(self._tick)

    # ---------- estado ----------
    def configure(self, mode, rgb, colorful, brightness, speed, direction):
        self.mode = mode
        self.rgb = tuple(c / 255 for c in rgb)
        self.colorful = colorful
        self.brightness, self.speed, self.direction = brightness, speed, direction
        self.queue_draw()

    def press(self, idx, real=True):
        k = self.by_idx.get(idx)
        if k:
            self.presses.append((k, self.t))
            if real:
                self._last_real = self.t

    # ---------- animação ----------
    def _tick(self, _w, clock):
        now = clock.get_frame_time() / 1e6
        if self._last_frame is not None and self.get_mapped():
            sp = 0.4 + 0.3 * self.speed
            self.t += min(now - self._last_frame, 0.1) * sp
            self.presses = [(k, tp) for k, tp in self.presses if self.t - tp < 3]
            if self.mode in REACTIVE and self.t - self._last_real > 2 and self.t >= self._next_fake:
                self.press(random.choice(self.keys).idx, real=False)
                self._next_fake = self.t + random.uniform(0.25, 0.7)
            self.queue_draw()
        self._last_frame = now
        return GLib.SOURCE_CONTINUE

    def _base(self, k, hue=None):
        if self.colorful:
            return hsv(k.nx * 0.85 if hue is None else hue)
        return self.rgb

    def _light(self, k):
        """Cor e intensidade (0..1) da tecla no instante atual."""
        t, m = self.t, self.mode
        d = -1 if self.direction else 1
        if m == 0x00:
            return self.rgb, 0.0
        if m == 0x01:
            return self._base(k), 1.0
        if m in (0x02, 0x03):
            hit = max((math.exp(-(t - tp) * 2.5) for kk, tp in self.presses if kk is k), default=0.0)
            return self._base(k, k.hue), hit if m == 0x02 else 1 - hit
        if m == 0x04:  # estrelas
            v = max(0.0, math.sin(2 * math.pi * (t * 0.35 + k.phase))) ** 6
            return self._base(k, k.hue), v
        if m == 0x05:  # neve caindo
            pos = (t * 0.18 + self.col_seed.get(k.col, 0)) % 1.3
            v = math.exp(-((k.ny - pos) / 0.07) ** 2)
            return (self.rgb if not self.colorful else (1, 1, 1)), v
        if m == 0x06:  # flores variadas
            v = max(0.0, math.sin(2 * math.pi * (t * 0.3 + k.phase))) ** 3
            return hsv(k.hue + t * 0.05), v
        if m == 0x07:  # respiração
            v = 0.08 + 0.92 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 3.5))
            return self._base(k, t * 0.06), v
        if m == 0x08:  # ciclo espectral
            return hsv(t * 0.08), 1.0
        if m == 0x09:  # jatos coloridos
            dist = math.hypot(k.nx - 0.42, (k.ny - 0.55) * 0.45)
            return hsv(dist * 1.6 - t * 0.25), 1.0
        if m == 0x0A:  # cores em movimento
            return hsv(k.nx - d * t * 0.15), 1.0
        if m == 0x0B:  # ondas
            v = 0.1 + 0.9 * max(0.0, math.cos(2 * math.pi * (k.nx * 1.4 - d * t * 0.3))) ** 2
            return self._base(k, k.nx - d * t * 0.1), v
        if m in (0x0C, 0x13):  # curvas e recuos / ida e volta
            pos = 0.5 + 0.52 * math.sin(t * 0.9)
            width = 0.09 if m == 0x0C else 0.04
            v = math.exp(-((k.nx - pos) / width) ** 2)
            return self._base(k, pos), v
        if m == 0x0D:  # pronto para disparar: a fileira acende
            v = max((math.exp(-(t - tp) * 1.8) * math.exp(-abs(k.nx - kk.nx) * 1.2)
                     for kk, tp in self.presses if kk.row == k.row), default=0.0)
            return self._base(k, k.hue), v
        if m == 0x0E:  # dois pássaros: dois pontos correndo pela fileira
            v = 0.0
            for kk, tp in self.presses:
                if kk.row == k.row:
                    front = (t - tp) * 0.6
                    v = max(v, math.exp(-((abs(k.nx - kk.nx) - front) / 0.035) ** 2) * math.exp(-(t - tp)))
            return self._base(k, k.hue), v
        if m == 0x0F:  # ondas de expansão
            v = 0.0
            for kk, tp in self.presses:
                dist = math.hypot(k.nx - kk.nx, (k.ny - kk.ny) * 0.35)
                v = max(v, math.exp(-((dist - (t - tp) * 0.45) / 0.03) ** 2) * math.exp(-(t - tp) * 0.8))
            return self._base(k, self.presses[-1][0].hue if self.presses else 0), v
        if m == 0x10:  # fluxo contínuo (diagonal)
            return hsv((k.nx + k.ny * 0.5) - d * t * 0.15), 1.0
        if m == 0x11:  # montanhas em camadas
            v = 0.15 + 0.85 * max(0.0, math.cos(2 * math.pi * (k.ny * 1.1 + t * 0.25))) ** 2
            return self._base(k, k.ny + t * 0.05), v
        if m == 0x12:  # chuva leve
            pos = (t * 0.35 + self.col_seed.get(k.col, 0) * 1.7) % 1.4 - 0.1
            if d < 0:
                pos = 1 - pos
            v = math.exp(-((k.ny - pos) / 0.06) ** 2)
            return self._base(k, k.col / 18), v
        if m == 0xFE:  # momento emocionante: coração pulsando
            sc = 1 + 0.12 * math.sin(t * 4)
            cx = (k.x + k.w / 2 - 7.4) / (3.3 * sc)
            cy = -(k.y + 0.5 - 3.1) / (2.6 * sc) + 0.2
            heart = (cx * cx + cy * cy - 1) ** 3 - cx * cx * cy ** 3
            return self._base(k), (1.0 if heart <= 0 else 0.0)
        return self._base(k), 1.0

    # ---------- desenho ----------
    def _layout(self, k, px):
        if self._font_px != px:
            self._layouts, self._font_px = {}, px
        lay = self._layouts.get(k.idx)
        if lay is None:
            lay = self.create_pango_layout(k.label)
            fd = Pango.FontDescription.from_string("Sans Bold")
            fd.set_absolute_size(px * Pango.SCALE)
            lay.set_font_description(fd)
            self._layouts[k.idx] = lay
        return lay

    def do_snapshot(self, snap):
        width, height = self.get_width(), self.get_height()
        unit = min((width - 24) / TOTAL_W, (height - 24) / TOTAL_H)
        if unit < 8:  # ainda sem tamanho útil
            return
        ox = (width - TOTAL_W * unit) / 2
        oy = (height - TOTAL_H * unit) / 2
        gap = max(2.0, unit * 0.07)
        bfac = 0.2 + 0.8 * (self.brightness - 1) / 4
        px = max(7.0, unit * 0.2)

        # carcaça
        case = rrect(ox - 12, oy - 12, TOTAL_W * unit + 24, TOTAL_H * unit + 24, 16)
        snap.append_outset_shadow(case, rgba(0, 0, 0, 0.35), 0, 8, 0, 24)
        snap.push_rounded_clip(case)
        snap.append_color(rgba(0.08, 0.085, 0.10), case.bounds)
        snap.pop()

        for k in self.keys:
            (r, g, b), v = self._light(k)
            v = max(0.0, min(1.0, v)) * bfac
            x, y = ox + k.x * unit + gap / 2, oy + k.y * unit + gap / 2
            w, h = k.w * unit - gap, unit - gap
            rad = unit * 0.14
            cap = rrect(x, y, w, h, rad)
            # luz vazando por baixo do keycap
            if v > 0.04:
                snap.append_outset_shadow(cap, rgba(r, g, b, 0.8 * v), 0, 0, 1, unit * 0.22)
            snap.push_rounded_clip(cap)
            snap.append_color(rgba(0.16 + 0.55 * r * v, 0.165 + 0.55 * g * v, 0.18 + 0.55 * b * v), cap.bounds)
            top = rrect(x + 2, y + 2, w - 4, h - unit * 0.18, rad * 0.8)
            snap.push_rounded_clip(top)
            snap.append_color(rgba(1, 1, 1, 0.05), top.bounds)
            snap.pop()
            snap.pop()
            # legenda iluminada
            lay = self._layout(k, px)
            _, logical = lay.get_pixel_extents()
            color = rgba(0.55 + 0.45 * r * v, 0.55 + 0.45 * g * v, 0.58 + 0.42 * b * v) if v > 0.05 \
                else rgba(0.42, 0.43, 0.47)
            snap.save()
            pt = Graphene.Point()
            pt.init(x + (w - logical.width) / 2, y + h * 0.42 - logical.height / 2)
            snap.translate(pt)
            snap.append_layout(lay, color)
            snap.restore()
