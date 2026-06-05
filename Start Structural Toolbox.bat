@echo off
chcp 65001 >nul
title Structural Toolbox
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
echo この黒い画面は閉じないでください（ログが表示されます）。
echo 終了するときはこの画面を閉じてください。
echo デバッグ用: 「Start Structural Toolbox (debug).bat」
echo.

call ".venv\Scripts\stb.exe" gui
set "RC=%ERRORLEVEL%"

echo.
if %RC% equ 10 (
    echo [お知らせ] すでに別の画面でサーバーが動いています。
    echo ログを見るには、その黒い画面を探してください。
    echo 完全に終了するには、その画面を閉じてから再度起動してください。
) else if %RC% neq 0 (
    echo [注意] 終了コード %RC%
) else (
    echo サーバーを終了しました。
)
echo.
pause
exit /b %RC%
