#!/usr/bin/env bash
# Windows embeddable package を TARGET_DIR/python-embed に展開・設定する（Linux 上で実行）
set -euo pipefail

TARGET_DIR="${1:?usage: fetch_embed_python.sh TARGET_DIR}"
VERSION_FILE="$(cd "$(dirname "$0")" && pwd)/PYTHON_EMBED_VERSION"
VERSION="$(tr -d '\r\n' < "$VERSION_FILE")"
MAJOR_MINOR="${VERSION%.*}"          # 3.12
PY_TAG="python${MAJOR_MINOR//./}"   # python312

EMBED_DIR="$TARGET_DIR/python-embed"
ZIP_NAME="python-${VERSION}-embed-amd64.zip"
URL="https://www.python.org/ftp/python/${VERSION}/${ZIP_NAME}"
# ビルド作業フォルダは消えるため、キャッシュは student/dist/_cache に置く
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE="${SCRIPT_DIR}/dist/_cache"
ZIP_PATH="$CACHE/${ZIP_NAME}"

mkdir -p "$CACHE"
echo "Fetching embeddable Python ${VERSION} ..."

if [[ ! -f "$ZIP_PATH" ]]; then
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$ZIP_PATH" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$ZIP_PATH" "$URL"
  else
    echo "error: need curl or wget" >&2
    exit 1
  fi
fi

rm -rf "$EMBED_DIR"
mkdir -p "$EMBED_DIR"
unzip -q -o "$ZIP_PATH" -d "$EMBED_DIR"

PTH_FILE="$EMBED_DIR/${PY_TAG}._pth"
if [[ ! -f "$PTH_FILE" ]]; then
  echo "error: ${PY_TAG}._pth not found in embed package" >&2
  ls -la "$EMBED_DIR" >&2
  exit 1
fi

mkdir -p "$EMBED_DIR/Lib/site-packages"
cat > "$PTH_FILE" <<EOF
${PY_TAG}.zip
.
Lib\\site-packages

import site
EOF

if command -v curl >/dev/null 2>&1; then
  curl -fsSL -o "$EMBED_DIR/get-pip.py" https://bootstrap.pypa.io/get-pip.py
else
  wget -q -O "$EMBED_DIR/get-pip.py" https://bootstrap.pypa.io/get-pip.py
fi

if [[ ! -f "$EMBED_DIR/python.exe" ]]; then
  echo "error: python.exe missing after extract" >&2
  exit 1
fi

echo "OK: python-embed (${VERSION}) -> $EMBED_DIR"
