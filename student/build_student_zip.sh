#!/usr/bin/env bash
# 教員用: Windows 学生向け ZIP（embeddable Python 同梱）を Linux から作成
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/student/dist"
STAMP="$(date +%Y%m%d)"
VERSION="$(tr -d '\r\n' < "$ROOT/student/PYTHON_EMBED_VERSION")"
NAME="StructuralToolbox_Windows_${STAMP}"
WORKDIR="$DIST/_build/$NAME"
ZIP="$DIST/${NAME}.zip"
FETCH="$ROOT/student/fetch_embed_python.sh"

cd "$ROOT"

echo "Building $ZIP (Python embed ${VERSION}) ..."

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR" "$DIST"

# コア（開発用ゴミ・ローカル venv / embed を除外）
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.venv-*' \
  --exclude='.venv_*' \
  --exclude='python-embed' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='tests/_tmp_out' \
  --exclude='student/dist' \
  --exclude='.idea' \
  --exclude='docs/element_stiffness_matrix.html' \
  "$ROOT/" "$WORKDIR/"

# Windows embeddable Python（要ネットワーク・初回は python.org から取得）
bash "$FETCH" "$WORKDIR"

# 必須ランチャー
for f in "Install_once.bat" "Start Structural Toolbox.bat"; do
  if [[ ! -f "$WORKDIR/$f" ]]; then
    echo "error: missing $f" >&2
    exit 1
  fi
done

if [[ ! -f "$WORKDIR/python-embed/python.exe" ]]; then
  echo "error: python-embed/python.exe missing" >&2
  exit 1
fi

# バージョン記録（学生・教員向け）
echo "Python ${VERSION} (Windows embeddable, 64-bit)" > "$WORKDIR/python-embed/VERSION.txt"

cp "$ROOT/docs/学生用_はじめ方_Windows.md" "$WORKDIR/はじめ方_Windows.md"

rm -f "$ZIP"
(cd "$DIST/_build" && zip -r -q "$ZIP" "$NAME")

# キャッシュは _build 親に残す（再ビルド高速化）
rm -rf "$DIST/_build/$NAME"
echo "Done: $ZIP"
echo "Size: $(du -h "$ZIP" | cut -f1)"
echo "Embedded Python: ${VERSION}"
echo ""
echo "学生へ: ZIP を解凍 → Install_once.bat → Start Structural Toolbox.bat"
