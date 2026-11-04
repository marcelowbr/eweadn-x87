#!/usr/bin/env bash
# Gera dist/eweadn-x87 (executável único) e dist/eweadn-x87_<versão>_all.deb
# Uso: scripts/build.sh
set -euo pipefail

APP_ID="io.github.eweadn.x87"
# mantenedor do .deb (e-mail noreply do GitHub); pode trocar com a variável MAINTAINER
MAINTAINER="${MAINTAINER:-Marcelo W. <112717310+marcelowbr@users.noreply.github.com>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/eweadn_x87/__init__.py")}"
DIST="$ROOT/dist"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

rm -rf "$DIST"
mkdir -p "$DIST"

# 1) executável único (zipapp: um .zip com o código, executado pelo python3 do sistema)
mkdir -p "$TMP/app"
cp -r "$ROOT/src/eweadn_x87" "$TMP/app/"
find "$TMP/app" -name __pycache__ -prune -exec rm -rf {} +
printf 'import sys\nfrom eweadn_x87.__main__ import main\nsys.exit(main())\n' > "$TMP/app/__main__.py"
python3 -m zipapp "$TMP/app" -o "$DIST/eweadn-x87" -p "/usr/bin/env python3" -c
chmod +x "$DIST/eweadn-x87"
echo "ok  $DIST/eweadn-x87"

# 2) pacote .deb
PKG="$TMP/deb"
install -Dm755 "$DIST/eweadn-x87" "$PKG/usr/bin/eweadn-x87"
install -Dm644 "$ROOT/packaging/$APP_ID.desktop" "$PKG/usr/share/applications/$APP_ID.desktop"
install -Dm644 "$ROOT/packaging/$APP_ID.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/$APP_ID.svg"
install -Dm644 "$ROOT/packaging/70-eweadn-x87.rules" "$PKG/usr/lib/udev/rules.d/70-eweadn-x87.rules"
mkdir -p "$PKG/DEBIAN"
cat > "$PKG/DEBIAN/control" <<EOF
Package: eweadn-x87
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1 (>= 1.5)
Maintainer: $MAINTAINER
Description: Configurador do teclado EWEADN X87 para Linux
 Bateria, iluminação RGB com pré-visualização, remapeamento de teclas
 (com e sem Fn) e modo de sono, pelo dongle 2.4G ou cabo USB.
EOF
cat > "$PKG/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules || true
    udevadm trigger --subsystem-match=hidraw || true
fi
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q /usr/share/icons/hicolor || true
EOF
chmod 755 "$PKG/DEBIAN/postinst"
dpkg-deb --root-owner-group --build "$PKG" "$DIST/eweadn-x87_${VERSION}_all.deb" >/dev/null
echo "ok  $DIST/eweadn-x87_${VERSION}_all.deb"
