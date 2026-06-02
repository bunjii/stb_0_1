# 仮想環境のセットアップ（複数 PC / Dropbox）

このプロジェクトは **GitHub でコードを共有**し、**仮想環境（`.venv` など）は各 PC でローカルに作る**運用を推奨します。

## なぜ venv を Git / Dropbox で共有しないか

- `.venv-win` を Git に入れていたため、`git status` が数千ファイルになり遅くなっていた
- Windows 用 venv を Linux に Dropbox 同期しても **バイナリが使えない**一方、同期・競合だけ発生する
- venv は **数 GB** になり、Dropbox の同期も重くなる

## 各 PC での初回セットアップ

```bash
cd /path/to/stb_0_1   # Dropbox 上のパスでも可

# 古い試用 venv があれば削除してよい（任意）
# rm -rf .venv-win .venv_win .venv_py314_broken

python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[viewer]"
```

動作確認:

```bash
.venv/bin/stb version
.venv/bin/stb solve examples/cantilever.dat -o /tmp/out.dat -q
```

## Windows の場合

プロジェクト直下で **名前は `.venv` に統一**（`.venv-win` は使わない）:

```powershell
cd C:\Users\...\Dropbox\98_codes\stb_0_1
py -3 -m venv .venv
.\.venv\Scripts\pip install -U pip
.\.venv\Scripts\pip install -e ".[viewer]"
```

## Dropbox で venv を同期しない（推奨）

`.gitignore` は **Git だけ**に効きます。Dropbox の同期量を減らすには、次のいずれかを行ってください。

### 方法 A: Dropbox でフォルダを「同期しない」

各 venv フォルダ（`.venv`, `.venv-win` など）を右クリック → **Dropbox に同期しない**（表記はクライアント版により異なります）。

### 方法 B: Linux で ignore 属性（Dropbox 公式）

```bash
cd /path/to/stb_0_1
attr -s com.dropbox.ignored -V 1 .venv
# 古いフォルダを残している場合
attr -s com.dropbox.ignored -V 1 .venv-win .venv_win .venv_py314_broken 2>/dev/null || true
```

設定後、不要な古い venv はローカルで削除し、上記「各 PC での初回セットアップ」で `.venv` を作り直してください。

### 方法 C: venv を Dropbox 外に置く

```bash
python3 -m venv ~/venvs/stb_0_1
~/venvs/stb_0_1/bin/pip install -e "/path/to/Dropbox/.../stb_0_1[viewer]"
```

## 依存関係を更新したあと

`pyproject.toml` を pull したら、各 PC で:

```bash
.venv/bin/pip install -e ".[viewer]"
```

## Git pull 後（venv 追跡をやめたコミット以降）

他の PC で `git pull` すると、リポジトリから `.venv-win` の追跡は消えます。ローカルにフォルダが残っていても Git には出ません。Dropbox で同期しない設定にしておくと安全です。
