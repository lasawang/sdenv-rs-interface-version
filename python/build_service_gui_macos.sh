#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${TMPDIR:-/tmp}/sdenv_pyinstaller_macos"
APP_NAME="sdenv-service-gui-macos-arm64"
APP_BUNDLE="${APP_NAME}.app"
DMG_NAME="${APP_NAME}.dmg"

cd "$ROOT_DIR"

echo "[1/4] Check platform..."
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS."
  exit 1
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "Warning: expected arm64 (Apple Silicon), current arch is: $ARCH"
  echo "The output may not match M-series target."
fi

echo "[2/4] Check PyInstaller..."
if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller is not installed."
  echo "Run: pip install pyinstaller"
  exit 1
fi

echo "[3/4] Build macOS arm64 executable and app bundle..."
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/spec" "$BUILD_ROOT/build" "$BUILD_ROOT/dist"
cp -f "python/sdenv_service_gui.py" "$BUILD_ROOT/sdenv_service_gui.py"

pyinstaller --noconfirm --clean --windowed --name "$APP_NAME" \
  --specpath "$BUILD_ROOT/spec" \
  --workpath "$BUILD_ROOT/build" \
  --distpath "$BUILD_ROOT/dist" \
  "$BUILD_ROOT/sdenv_service_gui.py"

mkdir -p "$ROOT_DIR/dist"
if [[ ! -d "$BUILD_ROOT/dist/$APP_BUNDLE" ]]; then
  echo "Build output $BUILD_ROOT/dist/$APP_BUNDLE not found."
  exit 1
fi

rm -rf "$ROOT_DIR/dist/$APP_BUNDLE"
cp -R "$BUILD_ROOT/dist/$APP_BUNDLE" "$ROOT_DIR/dist/$APP_BUNDLE"

# Extract launcher binary for CLI usage
cp -f "$ROOT_DIR/dist/$APP_BUNDLE/Contents/MacOS/$APP_NAME" "$ROOT_DIR/dist/$APP_NAME"
chmod +x "$ROOT_DIR/dist/$APP_NAME"

# Build DMG containing the .app bundle
rm -f "$ROOT_DIR/dist/$DMG_NAME"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$ROOT_DIR/dist/$APP_BUNDLE" \
  -ov \
  -format UDZO \
  "$ROOT_DIR/dist/$DMG_NAME"

echo "[4/4] Done."
echo "Binary: $ROOT_DIR/dist/$APP_NAME"
echo "App: $ROOT_DIR/dist/$APP_BUNDLE"
echo "DMG: $ROOT_DIR/dist/$DMG_NAME"
echo
echo "Usage:"
echo "1. Double click dist/$APP_BUNDLE or mount dist/$DMG_NAME."
echo "2. Service auto-starts on app launch (or click Start Service)."
echo "3. Call API from python/sdenv_client.py with the shown host/port."
