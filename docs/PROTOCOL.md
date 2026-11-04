# EWEADN X87 HID protocol

Reverse-engineered from the official web configurator (`hub.eweadn.cn`, `hfd87` module) and
verified on an X87 with firmware 1.19 through the 2.4 GHz dongle.

## Transport

The 2.4 GHz dongle (`0c45:fefe`) exposes five HID interfaces:

| Interface | Usage page | Purpose |
|---|---|---|
| 0 | Generic Desktop / Keyboard | Boot keyboard (8-byte reports) |
| 1 | Generic Desktop / Mouse | Mouse |
| 2 | Consumer, System, NKRO keyboard | Media and system keys |
| **3** | **`0xFF60`, usage `0x61`** | **Configuration channel (32-byte in/out reports)** |
| 4 | `0xFF59`, usage `0x61` | Vendor channel, 64-byte reports (unused here) |

All configuration happens on interface 3, through `/dev/hidrawN`. Reports have no report ID, so on
Linux every `write()` is prefixed with a `0x00` byte.

The `0xFF60` / `0x61` pair is the same one QMK/VIA uses, but the command set is different.

## Packet format

Host → keyboard, 32 bytes:

| Byte | Meaning |
|---|---|
| 0 | `0xAA` |
| 1 | Command |
| 2 | Payload length for this chunk (24 when the data fits in one chunk) |
| 3–4 | Offset into the data block, little-endian |
| 5 | `0` |
| 6 | `1` on the last chunk, else `0` |
| 7 | `0` |
| 8–31 | Payload (up to 24 bytes) |

Keyboard → host replies use the same layout with byte 0 = `0x55` and the same command. Every
chunk is acknowledged before the next one is sent. Blocks larger than 24 bytes are transferred as
consecutive chunks with increasing offsets.

`0x1X` commands **read** a block; `0x2X` (read + `0x10`) **write** the same block.

| Read | Write | Block | Size |
|---|---|---|---|
| `0x10` | – | Device info | 32 |
| `0x11` | `0x21` | Settings | 32 (write 16) |
| `0x12` | `0x22` | Keymap, normal layer | 512 |
| `0x13` | `0x23` | Lighting | 16 |
| `0x15` | `0x25` | Macros | 1024 |
| `0x16` | `0x26` | Keymap, Fn layer | 512 |
| `0x1B` | `0x2B` | Light box effects | 24 |

After writing settings (`0x21`), the official app also sends command `0x00` with a 4-byte zero payload.

## Device info (`0x10`)

Offsets are relative to the payload (byte 8 of the packet).

| Offset | Meaning |
|---|---|
| 4–5 | USB VID of the keyboard (LE), `0x0c45` |
| 6–7 | Wired PID (LE), `0x8006` |
| 8–9 | Firmware version: `(b8 & 0x0F) + 10 * (b8 >> 4) + 100 * b9`, divided by 100 (`0x19 0x01` → 1.19) |
| 12–13 | Vendor number (LE), `2` |
| 14–15 | Product number (LE), `5` = X87 |
| 17 | **Battery, %** |

## Settings (`0x11` / `0x21`)

| Offset | Meaning |
|---|---|
| 3 | **Sleep time in minutes**, `0` = sleep disabled (official app range: 1–30) |
| 4 | Response time |
| 5 | Polling-rate code |
| 6 | OS mode |
| 11 | Stability |

When writing, send 16 bytes with offsets 0–2 set to zero and the other fields copied from a read.

## Lighting (`0x13` / `0x23`)

| Offset | Meaning |
|---|---|
| 0 | Effect (see below), `0` = off |
| 1–3 | R, G, B |
| 4 | `0xFF` when writing |
| 5–7 | Secondary R, G, B |
| 8 | `1` = rainbow, `0` = single color |
| 9 | Brightness 1–5 |
| 10 | Speed 1–5 |
| 11 | Direction |
| 14–15 | `0xAA 0x55` when writing |

Effects: `0x01` static, `0x02` single key on, `0x03` single key off, `0x04` starry sky, `0x05`
snowfall, `0x06` blooming flowers, `0x07` breathing, `0x08` spectrum cycle, `0x09` color fountain,
`0x0A` moving colors, `0x0B` waves, `0x0C` twists and turns, `0x0D` one touch to fire, `0x0E` two
birds, `0x0F` ripples, `0x10` endless flow, `0x11` layered mountains, `0x12` gentle rain, `0x13`
back and forth, `0xFE` heartbeat, `0x80` custom per-key.

## Keymaps (`0x12`/`0x22` normal, `0x16`/`0x26` Fn layer)

512 bytes, **4 bytes per key**, indexed by the key's matrix position (`offset = 4 * index`).
All zeros means "factory default" for that key. Positions are listed in `LAYOUT` in
[`protocol.py`](../src/eweadn_x87/protocol.py) (e.g. Esc = 0, A = 49, Fn = 85, ↑ = 90).

| Action | Bytes |
|---|---|
| Default | `00 00 00 00` |
| Keyboard key | `02 00 <HID usage> 00` |
| Modifier | `02 <HID usage 0xE0–0xE7> 00 00` |
| Media / consumer key | `03 <usage lo> <usage hi> 00` |
| Mouse button | `01 01 <bit: 1 left, 2 right, 4 middle, 8 back, 16 forward> 00` |
| Mouse wheel | `01 03 <1 up / 0xFF down> 00` |
| Macro | `06 <macro index> <mode> <repeat count>` |

Fn + F1…F12 (indices 1–12) are locked by the official app.

Firmware behavior: while a remapped key is held, the keyboard sends repeated press/release pairs
about every 130 ms instead of a single held press.
