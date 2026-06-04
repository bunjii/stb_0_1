# 学生配布用（方針 B + 同梱 Python）

教員（Linux 開発環境）が **Windows 11 学生向け ZIP** を作るためのメモです。

## 特徴

- **Windows embeddable Python**（既定 3.12.10, 64-bit）を ZIP に同梱
- 学生 PC の **システム Python は使わない** → バージョンと環境を揃えやすい
- 初回 `Install_once.bat` で **同梱 Python から `.venv` を作成**（`virtualenv` 使用。embed には標準 `venv` が無い）し、パッケージをインストール

バージョン変更: `student/PYTHON_EMBED_VERSION` を編集してから ZIP を再ビルド。

## Linux から ZIP を作る

```bash
cd /path/to/stb_0_1
./student/build_student_zip.sh
```

- **初回はインターネット必須**（python.org から embed パッケージを取得）
- キャッシュ: `student/dist/_cache/`（2 回目以降は高速）
- 出力: `student/dist/StructuralToolbox_Windows_YYYYMMDD.zip`（約 12〜15 MB + プロジェクト）

## ZIP に含まれるもの

| 内容 | 説明 |
| --- | --- |
| `python-embed/` | 公式 embeddable package + `get-pip.py` |
| `Install_once.bat` | pip 導入 → `.venv` 作成 → `pip install -e ".[gui]"` |
| `Start Structural Toolbox.bat` | `stb gui` 起動 |
| `classes/`, `stb_*`, `examples/`, `data/`, … | プログラム本体 |
| `はじめ方_Windows.md` | 学生向け手順 |

## ZIP に含めないもの

- `.git/`, `.venv/`（学生 PC で初回作成）
- 教員用のローカル `python-embed`（リポジトリ直下に置かない）

## 学生 PC 上の流れ

1. ZIP をローカルに解凍
2. `Install_once.bat`（初回のみ・要ネット）
3. `Start Structural Toolbox.bat`（毎回）

フォルダ構成のイメージ:

```
StructuralToolbox_Windows_20260604/
  python-embed/          ← 同梱 Python（触らない）
  .venv/                 ← 初回セットアップで自動作成
  Install_once.bat
  Start Structural Toolbox.bat
  examples/
  data/
  ...
```

## Mac 学生

Windows 用 ZIP は使えません。Mac 用は別パッケージ（未整備）または教員サーバ方式を検討してください。

## 更新時

- 新 ZIP を配布
- 学生は **上書きまたは新フォルダ** に解凍し、`Install_once.bat` を再実行（推奨）
