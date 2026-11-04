"""Protocolo do teclado EWEADN X87 (dongle 2.4G 0c45:fefe / cabo 0c45:8006).

Engenharia reversa do hub web oficial (hub.eweadn.cn/hfd87). Pacotes de 32 bytes
na interface HID vendor 0xFF60/0x61:

    [0]=0xAA [1]=cmd [2]=len [3..4]=offset LE [5]=0 [6]=ultimo [7]=0 [8..31]=dados

Respostas chegam com [0]=0x55 e o mesmo layout. Comandos 0x1X leem, 0x2X gravam.
"""

import glob
import os
import select
import threading
import time

from .i18n import tr

VID = 0x0C45
PIDS = (0xFEFE, 0x8006)
PKT = 32
CHUNK = PKT - 8

CMD_INFO = 0x10
CMD_SETTINGS = 0x11
CMD_KEYS = 0x12
CMD_LED = 0x13
CMD_FN = 0x16
WRITE = 0x10  # somado ao comando de leitura

# Efeitos de luz (valor do firmware -> nome)
EFFECTS = [
    (0x00, "Desligado", False, False, False),
    (0x01, "Estático", False, False, True),
    (0x02, "Ponto único aceso", True, False, True),
    (0x03, "Ponto único apagado", True, False, True),
    (0x04, "Estrelas", True, False, True),
    (0x05, "Neve caindo", True, False, True),
    (0x06, "Flores variadas", True, False, False),
    (0x07, "Respiração", True, False, True),
    (0x08, "Ciclo espectral", True, False, False),
    (0x09, "Jatos coloridos", True, False, True),
    (0x0A, "Cores em movimento", True, True, True),
    (0x0B, "Ondas", True, True, True),
    (0x0C, "Curvas e recuos", True, True, True),
    (0x0D, "Pronto para disparar", True, False, True),
    (0x0E, "Dois pássaros", True, False, True),
    (0x0F, "Ondas de expansão", True, False, True),
    (0x10, "Fluxo contínuo", True, True, True),
    (0x11, "Montanhas em camadas", True, False, True),
    (0x12, "Chuva leve", True, True, True),
    (0x13, "Ida e volta", True, False, True),
    (0xFE, "Momento emocionante", True, False, True),
]
# (valor, nome, tem_velocidade, tem_direcao, tem_cor)

BRIGHT_MAX = 5
SPEED_MAX = 5

# Layout físico: (índice no firmware, rótulo, código HID padrão)
LAYOUT = [
    [(0, "Esc", 41), (1, "F1", 58), (2, "F2", 59), (3, "F3", 60), (4, "F4", 61), (5, "F5", 62),
     (6, "F6", 63), (7, "F7", 64), (8, "F8", 65), (9, "F9", 66), (10, "F10", 67), (11, "F11", 68),
     (12, "F12", 69), (99, "PrtSc", 70), (100, "ScrLk", 71), (102, "Pause", 72)],
    [(16, "`", 53), (17, "1", 30), (18, "2", 31), (19, "3", 32), (20, "4", 33), (21, "5", 34),
     (22, "6", 35), (23, "7", 36), (24, "8", 37), (25, "9", 38), (26, "0", 39), (27, "-", 45),
     (28, "=", 46), (92, "Backspace", 42), (103, "Ins", 73), (104, "Home", 74), (105, "PgUp", 75)],
    [(32, "Tab", 43), (33, "Q", 20), (34, "W", 26), (35, "E", 8), (36, "R", 21), (37, "T", 23),
     (38, "Y", 28), (39, "U", 24), (40, "I", 12), (41, "O", 18), (42, "P", 19), (43, "[", 47),
     (44, "]", 48), (60, "\\", 49), (106, "Del", 76), (107, "End", 77), (108, "PgDn", 78)],
    [(48, "Caps", 57), (49, "A", 4), (50, "S", 22), (51, "D", 7), (52, "F", 9), (53, "G", 10),
     (54, "H", 11), (55, "J", 13), (56, "K", 14), (57, "L", 15), (58, ";", 51), (59, "'", 52),
     (76, "Enter", 40)],
    [(64, "Shift", 225), (65, "Z", 29), (66, "X", 27), (67, "C", 6), (68, "V", 25), (69, "B", 5),
     (70, "N", 17), (71, "M", 16), (72, ",", 54), (73, ".", 55), (74, "/", 56), (75, "Shift D", 229),
     (90, "↑", 82)],
    [(80, "Ctrl", 224), (81, "Win", 227), (82, "Alt", 226), (83, "Espaço", 44), (84, "Alt D", 230),
     (85, "Fn", 0), (86, "Menu", 101), (87, "Ctrl D", 228), (88, "←", 80), (89, "↓", 81), (91, "→", 79)],
]

# Símbolo de cima do keycap (com Shift), por código HID
SHIFTED = {53: "~", 30: "!", 31: "@", 32: "#", 33: "$", 34: "%", 35: "^", 36: "&", 37: "*",
           38: "(", 39: ")", 45: "_", 46: "+", 47: "{", 48: "}", 49: "|", 51: ":", 52: '"',
           54: "<", 55: ">", 56: "?"}

# Ícones das teclas especiais, por código HID
ICONS = {42: "⌫", 43: "⇥", 57: "⇪", 40: "⏎", 225: "⇧", 229: "⇧", 227: "⊞", 101: "☰"}

MODIFIERS = {224: "Ctrl esq.", 225: "Shift esq.", 226: "Alt esq.", 227: "Win esq.",
             228: "Ctrl dir.", 229: "Shift dir.", 230: "Alt dir.", 231: "Win dir."}

EXTRA_KEYS = {
    **{0x68 + i: f"F{13 + i}" for i in range(12)},
    0x53: "Num Lock", 0x54: "Num /", 0x55: "Num *", 0x56: "Num -", 0x57: "Num +", 0x58: "Num Enter",
    **{0x59 + i: f"Num {(i + 1) % 10}" for i in range(10)}, 0x63: "Num .",
    0x64: "Tecla extra ABNT2 (ao lado do Shift esq.)",
    0x87: "Tecla extra ABNT2 (ao lado do Shift dir.)",
}

FN_INDEX = 85
# Fn+F1..F12 têm funções de fábrica que o hub oficial não deixa trocar
FN_LOCKED = set(range(1, 13)) | {FN_INDEX}

# Código HID (usage) -> código evdev do Linux (tabela hid_keyboard[] do kernel)
_HID_EVDEV_ROWS = [
    0, 0, 0, 0, 30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38,
    50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44, 2, 3,
    4, 5, 6, 7, 8, 9, 10, 11, 28, 1, 14, 15, 57, 12, 13, 26,
    27, 43, 0, 39, 40, 41, 51, 52, 53, 58, 59, 60, 61, 62, 63, 64,
    65, 66, 67, 68, 87, 88, 99, 70, 119, 110, 102, 104, 111, 107, 109, 106,
    105, 108, 103, 69, 98, 55, 74, 78, 96, 79, 80, 81, 75, 76, 77, 71,
    72, 73, 82, 83, 86, 127, 0, 117, 183, 184, 185, 186, 187, 188, 189, 190,
    191, 192, 193, 194,
]
HID_TO_EVDEV = {h: e for h, e in enumerate(_HID_EVDEV_ROWS) if e}
HID_TO_EVDEV.update({0x87: 89, 224: 29, 225: 42, 226: 56, 227: 125, 228: 97, 229: 54, 230: 100, 231: 126})
EVDEV_TO_HID = {e: h for h, e in HID_TO_EVDEV.items()}

MEDIA = [(205, "Reproduzir/Pausar"), (183, "Parar"), (182, "Anterior"), (181, "Próxima"),
         (233, "Volume +"), (234, "Volume -"), (226, "Silenciar"), (402, "Calculadora"),
         (404, "Meu computador"), (394, "E-mail"), (387, "Multimídia"), (547, "Navegador: início"),
         (551, "Navegador: atualizar"), (549, "Navegador: avançar"), (548, "Navegador: voltar"),
         (554, "Favoritos"), (545, "Pesquisar")]

MOUSE = [((1, 1), "Mouse: botão esquerdo"), ((1, 2), "Mouse: botão direito"),
         ((1, 4), "Mouse: botão do meio"), ((1, 8), "Mouse: voltar"), ((1, 16), "Mouse: avançar"),
         ((3, 1), "Mouse: rolar para cima"), ((3, 255), "Mouse: rolar para baixo")]


def key_name(hid):
    for row in LAYOUT:
        for _, label, code in row:
            if code == hid and code:
                return f"{label} {SHIFTED[hid]}" if hid in SHIFTED else tr(label)
    name = MODIFIERS.get(hid) or EXTRA_KEYS.get(hid)
    return tr(name) if name else f"HID 0x{hid:02x}"


def action_keyboard(hid):
    """Ação de 4 bytes para uma tecla comum ou modificador."""
    return bytes([2, hid, 0, 0]) if hid in MODIFIERS else bytes([2, 0, hid, 0])


def action_media(usage):
    return bytes([3, usage & 0xFF, usage >> 8, 0])


def action_mouse(kind, value):
    return bytes([1, kind, value, 0])


def describe_action(a):
    a = bytes(a)
    if a == b"\0\0\0\0":
        return None
    if a[0] == 2:
        return key_name(a[1] or a[2])
    if a[0] == 3:
        usage = a[1] | (a[2] << 8)
        name = dict(MEDIA).get(usage)
        return tr(name) if name else tr("Mídia 0x{:03x}").format(usage)
    if a[0] == 1:
        name = dict(MOUSE).get((a[1], a[2]))
        return tr(name) if name else f"Mouse {a[1]}/{a[2]}"
    if a[0] == 6:
        return f"Macro {a[1]}"
    return tr("Ação {}").format(a.hex())


class X87Error(Exception):
    pass


def find_hidraw():
    """Acha o /dev/hidrawN da interface de configuração (usage page 0xFF60)."""
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            uevent = open(f"{node}/device/uevent").read()
            desc = open(f"{node}/device/report_descriptor", "rb").read()
        except OSError:
            continue
        hid_id = next((l.split("=")[1] for l in uevent.splitlines() if l.startswith("HID_ID=")), "")
        parts = hid_id.split(":")
        if len(parts) != 3 or int(parts[1], 16) != VID or int(parts[2], 16) not in PIDS:
            continue
        if desc.startswith(b"\x06\x60\xff"):
            return "/dev/" + os.path.basename(node), int(parts[2], 16)
    return None, None


class X87:
    def __init__(self):
        self.path, self.pid = find_hidraw()
        if not self.path:
            raise X87Error(tr("Teclado X87 não encontrado (dongle 2.4G ou cabo)."))
        try:
            self.fd = os.open(self.path, os.O_RDWR)
        except PermissionError:
            raise X87Error(tr("Sem permissão para abrir {}.").format(self.path))
        self.lock = threading.Lock()

    @property
    def wireless(self):
        return self.pid == 0xFEFE

    def close(self):
        os.close(self.fd)

    def _drain(self):
        while select.select([self.fd], [], [], 0)[0]:
            os.read(self.fd, 64)

    def _xfer(self, cmd, ln, off, last, data=b"", timeout=1.5):
        pkt = bytearray(PKT)
        pkt[0:8] = bytes([0xAA, cmd, ln, off & 0xFF, off >> 8, 0, 1 if last else 0, 0])
        pkt[8:8 + len(data)] = data
        os.write(self.fd, b"\x00" + bytes(pkt))
        end = time.monotonic() + timeout
        while (left := end - time.monotonic()) > 0:
            if select.select([self.fd], [], [], left)[0]:
                r = os.read(self.fd, 64)
                if len(r) >= 8 and r[0] == 0x55 and r[1] == cmd:
                    return r
        raise X87Error(tr("Sem resposta do teclado (cmd 0x{:02x}). Ele está ligado?").format(cmd))

    def read(self, cmd, size):
        with self.lock:
            self._drain()
            buf = bytearray(size)
            n = -(-size // CHUNK)
            for i in range(n):
                off = i * CHUNK
                r = self._xfer(cmd, min(CHUNK, size - off), off, i == n - 1)
                roff, rlen = r[3] | (r[4] << 8), r[2]
                buf[roff:roff + rlen] = r[8:8 + rlen]
            return buf

    def write(self, cmd, data):
        """Grava igual ao hub oficial (sendReportSuper): blocos de 24 bytes com ack."""
        data = bytes(data)
        with self.lock:
            self._drain()
            n = -(-len(data) // CHUNK)
            rem = len(data) % CHUNK
            for i in range(n):
                last = i == n - 1
                ln = rem if (last and i != 0 and rem) else CHUNK
                self._xfer(cmd, ln, i * CHUNK, last, data[i * CHUNK:(i + 1) * CHUNK])

    # --- leitura de alto nível ---
    def info(self):
        d = self.read(CMD_INFO, 32)
        return {
            "firmware": f"{((d[8] & 15) + 10 * (d[8] >> 4) + 100 * d[9]) / 100:.2f}",
            "battery": d[17],
            "vendor_no": d[12] | (d[13] << 8),
            "product_no": d[14] | (d[15] << 8),
        }

    def settings(self):
        return self.read(CMD_SETTINGS, 32)

    def led(self):
        d = self.read(CMD_LED, 16)
        return {
            "mode": d[0], "rgb": (d[1], d[2], d[3]), "colorful": bool(d[8]),
            "brightness": d[9], "speed": d[10], "direction": d[11], "raw": d,
        }

    def keymap(self):
        return self.read(CMD_KEYS, 512)

    def fn_keymap(self):
        """Ação de cada tecla com Fn pressionado (zero = função de fábrica)."""
        return self.read(CMD_FN, 512)

    # --- gravação de alto nível ---
    def set_led(self, mode=None, rgb=None, colorful=None, brightness=None, speed=None, direction=None):
        cur = self.led()
        p = bytearray(cur["raw"])
        if mode is not None:
            p[0] = mode
        if rgb is not None:
            p[1:4] = bytes(rgb)
        p[4] = 255
        if colorful is not None:
            p[8] = 1 if colorful else 0
        if brightness is not None:
            p[9] = max(1, min(BRIGHT_MAX, brightness))
        if speed is not None:
            p[10] = max(1, min(SPEED_MAX, speed))
        if direction is not None:
            p[11] = direction
        p[14], p[15] = 0xAA, 0x55
        self.write(CMD_LED + WRITE, p)

    def sleep_minutes(self):
        return self.settings()[3]

    def set_sleep_minutes(self, minutes):
        """0 desliga o modo de sono."""
        s = self.settings()
        p = bytearray(16)
        p[3] = max(0, min(255, minutes))
        for i in (4, 5, 6, 7, 8, 9, 11, 14, 15):
            p[i] = s[i]
        self.write(CMD_SETTINGS + WRITE, p)
        self.write(0x00, b"\0\0\0\0")

    def set_key(self, index, action):
        km = self.keymap()
        km[4 * index:4 * index + 4] = bytes(action)
        self.write(CMD_KEYS + WRITE, km)

    def set_fn_key(self, index, action):
        if index in FN_LOCKED:
            raise X87Error(tr("Fn+F1…F12 são fixas de fábrica."))
        km = self.fn_keymap()
        km[4 * index:4 * index + 4] = bytes(action)
        self.write(CMD_FN + WRITE, km)

    def reset_keys(self):
        self.write(CMD_KEYS + WRITE, bytes(512))

    def reset_fn(self):
        self.write(CMD_FN + WRITE, bytes(512))
