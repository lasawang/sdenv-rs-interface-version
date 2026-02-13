#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${TMPDIR:-/tmp}/sdenv_pyinstaller_macos"

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

echo "[3/4] Build macOS arm64 executable..."
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/spec" "$BUILD_ROOT/build" "$BUILD_ROOT/dist"
cp -f "python/sdenv_service_gui.py" "$BUILD_ROOT/sdenv_service_gui.py"

pyinstaller --noconfirm --clean --onefile --windowed --name sdenv-service-gui-macos-arm64 \
  --specpath "$BUILD_ROOT/spec" \
  --workpath "$BUILD_ROOT/build" \
  --distpath "$BUILD_ROOT/dist" \
  "$BUILD_ROOT/sdenv_service_gui.py"

mkdir -p "$ROOT_DIR/dist"
cp -f "$BUILD_ROOT/dist/sdenv-service-gui-macos-arm64" "$ROOT_DIR/dist/sdenv-service-gui-macos-arm64"
chmod +x "$ROOT_DIR/dist/sdenv-service-gui-macos-arm64"

echo "[4/4] Done."
echo "Binary: $ROOT_DIR/dist/sdenv-service-gui-macos-arm64"
echo
echo "Usage:"
echo "1. Run: ./dist/sdenv-service-gui-macos-arm64"
echo "2. Service auto-starts on app launch (or click Start Service)."
echo "3. Call API from python/sdenv_client.py with the shown host/port."

