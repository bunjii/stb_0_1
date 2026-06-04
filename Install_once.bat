@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM ZIP 解凍フォルダ直下で実行。同梱の python-embed のみ使用（PC 全体の Python は使いません）。
cd /d "%~dp0"

set "EMBED_DIR=%~dp0python-embed"
set "PY=%EMBED_DIR%\python.exe"

echo.
echo ========================================
echo  Structural Toolbox - 初回セットアップ
echo ========================================
echo.

if not exist "%PY%" (
    echo [エラー] 同梱の Python が見つかりません: python-embed\
    echo  ZIP が壊れているか、フォルダ構成が正しくない可能性があります。
    echo  教員に連絡してください。
    echo.
    pause
    exit /b 1
)

echo 使用する Python（同梱）:
"%PY%" --version
echo 場所: %EMBED_DIR%
echo.

REM --- 同梱 Python に pip を入れる（初回のみ） ---
if not exist "%EMBED_DIR%\Scripts\pip.exe" (
    if not exist "%EMBED_DIR%\get-pip.py" (
        echo [エラー] get-pip.py がありません。
        pause
        exit /b 1
    )
    echo pip を同梱 Python に導入しています...
    "%PY%" "%EMBED_DIR%\get-pip.py" --no-warn-script-location
    if errorlevel 1 (
        echo [エラー] pip の導入に失敗しました。
        pause
        exit /b 1
    )
)

REM --- 仮想環境（プロジェクト専用 .venv）---
REM 同梱の embeddable Python には標準の venv モジュールが無いため virtualenv を使用
if exist ".venv\Scripts\python.exe" (
    echo 既存の .venv があります。パッケージを更新します...
) else (
    echo virtualenv を導入しています...
    "%PY%" -m pip install virtualenv
    if errorlevel 1 (
        echo [エラー] virtualenv のインストールに失敗しました。
        pause
        exit /b 1
    )
    echo 仮想環境 .venv を作成しています（同梱 Python から・数分かかることがあります）...
    "%PY%" -m virtualenv .venv
    if errorlevel 1 (
        echo [エラー] .venv の作成に失敗しました。
        pause
        exit /b 1
    )
)

echo.
echo 必要なライブラリをインストールしています（初回は 5〜15 分・要インターネット）...
".venv\Scripts\python.exe" -m pip install -U pip
if errorlevel 1 goto :pipfail

".venv\Scripts\pip.exe" install -e ".[gui]"
if errorlevel 1 goto :pipfail

echo.
echo ========================================
echo  セットアップ完了
echo ========================================
echo.
echo 同梱 Python + このフォルダ専用の .venv で動作します。
echo PC に入っている別の Python とは混ざりません。
echo.
echo 次回からは「Start Structural Toolbox.bat」をダブルクリックしてください。
echo.
pause
exit /b 0

:pipfail
echo.
echo [エラー] パッケージのインストールに失敗しました。
echo インターネット接続を確認し、Install_once.bat を再実行してください。
echo.
pause
exit /b 1
