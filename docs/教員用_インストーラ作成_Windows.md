# 教員用 — Windows インストーラ（Setup.exe）の作成

学生には **ZIP + .bat** の代わりに、通常の Windows ソフトのように **Setup.exe** を配布できます。

---

## 必要なもの

| 環境 | 用途 |
| --- | --- |
| **Linux**（または WSL） | 同梱 Python 入り ZIP の作成（従来どおり） |
| **Windows 11** | Inno Setup で Setup.exe をビルド |
| [Inno Setup 6](https://jrsoftware.org/isdl.php) | 無料・インストールのみ |

---

## 手順

### 1. 配布用フォルダ / ZIP を作る

**Linux:**

```bash
cd /path/to/stb_0_1
./student/build_student_zip.sh
```

**Windows（Linux が無い場合）:**

```powershell
.\student\build_student_zip.ps1
```

出力例:

- `student/dist/_build/StructuralToolbox_Windows_YYYYMMDD/`（フォルダ）
- `student/dist/StructuralToolbox_Windows_YYYYMMDD.zip`（任意）

### 2. Setup.exe を作る（Windows）

PowerShell でリポジトリ直下から:

```powershell
.\student\build_student_installer.ps1
```

フォルダを直接指定する場合（ZIP 不要）:

```powershell
.\student\build_student_installer.ps1 -SourceDir student\dist\_build\StructuralToolbox_Windows_20260605
```

最新の `StructuralToolbox_Windows_*.zip` を自動で使います。明示する場合:

```powershell
.\student\build_student_installer.ps1 -ZipPath student\dist\StructuralToolbox_Windows_20260605.zip
```

出力例: `student/dist/StructuralToolbox_Setup_20260605.exe`（ZIP よりやや大きい）

### 3. 学生へ配布

- **配布物:** `StructuralToolbox_Setup_YYYYMMDD.exe` のみでよい
- 学生手順: Setup.exe をダブルクリック → ウィザード → 完了後、スタートメニュー／デスクトップの **Structural Toolbox** から起動

詳細は [学生用_インストール_Windows.md](学生用_インストール_Windows.md)

---

## インストール先

既定: `%LOCALAPPDATA%\StructuralToolbox`（管理者権限不要）

アンインストール: Windows の「アプリと機能」またはスタートメニューの Uninstall から。

---

## ZIP 配布との併用

- **Setup.exe** … 推奨（.bat を意識しない）
- **ZIP + Install_once.bat** … 従来方式（インストーラが使えない環境向け）

どちらも中身は同じ（同梱 Python + `.venv` + `stb gui` + Grasshopper `.gha`）。

配布用ペイロードには `grasshopper\StbGrasshopper.gha` が含まれます。Setup.exe
実行時に `%APPDATA%\Grasshopper\Libraries` が存在すれば、そこへ自動コピーされます。
Rhino/Grasshopperが起動中でコピーできない場合は、Rhinoを終了してから
インストール先の `Install_once.bat` を再実行してください。

---

## トラブル

| 症状 | 対処 |
| --- | --- |
| Inno Setup が見つからない | 公式サイトからインストール後、PowerShell を開き直す |
| インストール中に失敗 | 学生 PC のインターネットを確認。`%LOCALAPPDATA%\StructuralToolbox\install.log` を確認 |
| セットアップのみ再実行 | スタートメニュー「初回セットアップを再実行」または `Install_once.bat` |

---

## ファイル一覧

| ファイル | 説明 |
| --- | --- |
| `student/StructuralToolbox.iss` | Inno Setup 定義 |
| `student/build_student_installer.ps1` | ZIP → Setup.exe ビルド |
| `grasshopper\StbGrasshopper.gha` | インストーラーに同梱するGrasshopperプラグイン |
| `student/installer_info_before.txt` | インストール前の説明 |
| `student/installer_info_after.txt` | 完了後の説明 |
