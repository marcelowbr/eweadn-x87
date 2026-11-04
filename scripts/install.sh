#!/usr/bin/env bash
# Instala só para o usuário atual, sem sudo (use "scripts/install.sh --remover" para desinstalar)
set -euo pipefail

APP_ID="io.github.eweadn.x87"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$HOME/.local/bin/eweadn-x87"
DESKTOP="$HOME/.local/share/applications/$APP_ID.desktop"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/$APP_ID.svg"

if [[ "${1:-}" == "--remover" ]]; then
    rm -f "$BIN" "$DESKTOP" "$ICON"
    echo "EWEADN X87 removido."
    exit 0
fi

"$ROOT/scripts/build.sh" >/dev/null

install -Dm755 "$ROOT/dist/eweadn-x87" "$BIN"
install -Dm644 "$ROOT/packaging/$APP_ID.svg" "$ICON"
mkdir -p "$(dirname "$DESKTOP")"
sed "s|^Exec=.*|Exec=$BIN|" "$ROOT/packaging/$APP_ID.desktop" > "$DESKTOP"
command -v update-desktop-database >/dev/null && update-desktop-database -q "$(dirname "$DESKTOP")" || true

echo "Instalado: procure \"EWEADN X87\" no menu de aplicativos, ou rode: eweadn-x87"
