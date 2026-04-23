#!/usr/bin/env bash
# Baut PyInstaller onedir, dann .deb und AppImage (x86_64).
# Setzt OPENSTAIR_VERSION oder liest pyproject.toml / GITHUB_REF_NAME.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -n "${OPENSTAIR_VERSION:-}" ]]; then
  VERSION="$OPENSTAIR_VERSION"
elif [[ -n "${GITHUB_REF_NAME:-}" ]] && [[ "${GITHUB_REF_NAME}" == v* ]]; then
  VERSION="${GITHUB_REF_NAME#v}"
else
  VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
fi

echo "OpenStair build version: $VERSION"

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq \
  libxcb-cursor0 libegl1 libfontconfig1 \
  file \
  dpkg-dev \
  wget ca-certificates

python3 -m pip install --upgrade pip
# Laufzeit-Abhaengigkeiten ohne pytest (Bundle)
pip install "pyinstaller>=6.0,<7" "PySide6>=6.5,<7" "ezdxf>=1.0,<2" "reportlab>=4.0,<5"

rm -rf build dist packaging/_artifacts
mkdir -p packaging/_artifacts

pyinstaller --clean --noconfirm packaging/pyinstaller/openstair.spec

DISTDIR="$ROOT/dist/openstair"
if [[ ! -x "$DISTDIR/openstair" ]]; then
  echo "PyInstaller: erwartet $DISTDIR/openstair" >&2
  exit 1
fi

# --- .deb ---
PKGROOT="$ROOT/packaging/_debroot"
rm -rf "$PKGROOT"
mkdir -p "$PKGROOT/DEBIAN" "$PKGROOT/opt/openstair" "$PKGROOT/usr/bin" "$PKGROOT/usr/share/applications" "$PKGROOT/usr/share/pixmaps"

cp -a "$DISTDIR/." "$PKGROOT/opt/openstair/"

cat > "$PKGROOT/usr/bin/openstair" << 'EOF'
#!/bin/bash
exec /opt/openstair/openstair "$@"
EOF
chmod 0755 "$PKGROOT/usr/bin/openstair"

ICON_SRC="$ROOT/app/openstair-icon.png"
if [[ -f "$ICON_SRC" ]]; then
  cp -a "$ICON_SRC" "$PKGROOT/usr/share/pixmaps/openstair.png"
fi

cat > "$PKGROOT/usr/share/applications/openstair.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=OpenStair
Comment=Stahltreppen Vorplanung
Exec=openstair
Icon=openstair
Terminal=false
Categories=Engineering;Science;
EOF

cat > "$PKGROOT/DEBIAN/control" << EOF
Package: openstair
Version: $VERSION
Section: science
Priority: optional
Architecture: amd64
Maintainer: OpenStair CI <build@local>
Depends: libgl1, libegl1, libfontconfig1, libfreetype6, libx11-6, libxcb-cursor0, libxcb1, libxkbcommon0, libdbus-1-3, zlib1g
Description: OpenStair – Stahltreppen Vorplanung (GUI)
 Qt/PySide6-Anwendung; gebündelt unter /opt/openstair.
EOF

cat > "$PKGROOT/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 0755 "$PKGROOT/DEBIAN/postinst"

dpkg-deb --root-owner-group --build "$PKGROOT" "packaging/_artifacts/openstair_${VERSION}_amd64.deb"

# --- AppImage (AppDir) ---
APPDIR="$ROOT/packaging/_AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# PyInstaller-onedir komplett nach usr/bin (Binary + Qt-Plugins + .so)
cp -a "$DISTDIR/." "$APPDIR/usr/bin/"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
cd "${HERE}/usr/bin"
exec ./openstair "$@"
EOF
chmod 0755 "$APPDIR/AppRun"

if [[ -f "$ICON_SRC" ]]; then
  cp -a "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/256x256/apps/openstair.png"
  cp -a "$ICON_SRC" "$APPDIR/openstair.png"
fi

cat > "$APPDIR/openstair.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=OpenStair
Comment=Stahltreppen Vorplanung
Exec=openstair
Icon=openstair
Terminal=false
Categories=Engineering;Science;
X-AppImage-Version=$VERSION
EOF
cp -a "$APPDIR/openstair.desktop" "$APPDIR/usr/share/applications/openstair.desktop"

# appimagetool (ohne FUSE auf CI: --appimage-extract-and-run oder download portable)
APITOOL="$ROOT/packaging/_appimagetool.AppImage"
wget -q -O "$APITOOL" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x "$APITOOL"
export APPIMAGETOOL_EXTRACT_AND_RUN=1
ARCH=x86_64 VERSION="$VERSION" \
  "$APITOOL" --no-appstream \
  "$APPDIR" "packaging/_artifacts/OpenStair-${VERSION}-x86_64.AppImage"

ls -la packaging/_artifacts/
