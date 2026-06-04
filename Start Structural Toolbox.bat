@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\stb.exe" (
    echo.
    echo [お知らせ] 初回セットアップがまだです。
    echo 「Install_once.bat」をダブルクリックしてから、もう一度起動してください。
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Structural Toolbox
echo ========================================
echo.
echo ブラウザが開きます。
echo この黒い画面は閉じないでください。
echo 終了するときは Ctrl+C を押すか、この画面を閉じてください。
echo.

".venv\Scripts\stb.exe" gui
set "RC=%ERRORLEVEL%"

if %RC% neq 0 (
    echo.
    echo [エラー] 起動に失敗しました（コード %RC%）。
    echo Install_once.bat を再実行するか、docs\学生用_はじめ方_Windows.md を参照してください。
    echo.
    pause
)

exit /b %RC%
