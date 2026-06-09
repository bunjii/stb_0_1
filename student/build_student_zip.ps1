#Requires -Version 5.1
<#
.SYNOPSIS
  Windows 学生向け ZIP（同梱 Python）を作成する（Linux の build_student_zip.sh 相当）

.EXAMPLE
  .\student\build_student_zip.ps1
  .\student\build_student_zip.ps1 -SkipZip   # インストーラ用にフォルダだけ用意
#>
param(
    [switch]$SkipZip
)

$ErrorActionPreference = 'Stop'
$StudentDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $StudentDir
$DistDir = Join-Path $StudentDir 'dist'
$BuildStamp = Get-Date -Format 'yyyyMMdd'
$Name = "StructuralToolbox_Windows_$BuildStamp"
$WorkDir = Join-Path $DistDir "_build\$Name"
$ZipPath = Join-Path $DistDir "$Name.zip"
$Version = (Get-Content -LiteralPath (Join-Path $StudentDir 'PYTHON_EMBED_VERSION') -Raw).Trim()

$ExcludeDirNames = @(
    '.git', '.venv', '.venv-win', '.venv_win', '.venv_py314_broken',
    'python-embed', '__pycache__', '.pytest_cache', 'student', '.idea',
    'tests\_tmp_out', '.vscode', 'structural_toolbox.egg-info'
)
$ExcludeFilePatterns = @('*.pyc')

function Copy-StudentPayload {
    param([string]$Dest)
    if (Test-Path -LiteralPath $Dest) {
        Remove-Item -LiteralPath $Dest -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null

    $ExcludeFileNames = @('Presentation1.pptx')
    Get-ChildItem -LiteralPath $RepoRoot -Force -File | ForEach-Object {
        if ($ExcludeFileNames -contains $_.Name) { return }
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Dest $_.Name) -Force
    }

    Get-ChildItem -LiteralPath $RepoRoot -Force -Directory | ForEach-Object {
        if ($ExcludeDirNames -contains $_.Name) { return }
        if ($_.Name -eq 'docs') {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Dest 'docs') -Recurse -Force
            $skipHtml = Join-Path $Dest 'docs\element_stiffness_matrix.html'
            if (Test-Path -LiteralPath $skipHtml) { Remove-Item -LiteralPath $skipHtml -Force }
            return
        }
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Dest $_.Name) -Recurse -Force
    }

    $tmpOut = Join-Path $Dest 'tests\_tmp_out'
    if (Test-Path -LiteralPath $tmpOut) {
        Remove-Item -LiteralPath $tmpOut -Recurse -Force
    }

    Get-ChildItem -LiteralPath $Dest -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $Dest -Recurse -File -Filter '*.pyc' -ErrorAction SilentlyContinue |
        Remove-Item -Force

}

function Install-EmbedPython {
    param([string]$TargetDir)
    $MajorMinor = ($Version -split '\.')[0,1] -join '.'
    $PyTag = "python$($MajorMinor.Replace('.',''))"
    $EmbedDir = Join-Path $TargetDir 'python-embed'
    $ZipName = "python-$Version-embed-amd64.zip"
    $Url = "https://www.python.org/ftp/python/$Version/$ZipName"
    $CacheDir = Join-Path $DistDir '_cache'
    $CacheZip = Join-Path $CacheDir $ZipName

    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    if (-not (Test-Path -LiteralPath $CacheZip)) {
        Write-Host "Downloading embeddable Python $Version ..."
        Invoke-WebRequest -Uri $Url -OutFile $CacheZip -UseBasicParsing
    } else {
        Write-Host "Using cached: $CacheZip"
    }

    if (Test-Path -LiteralPath $EmbedDir) {
        Remove-Item -LiteralPath $EmbedDir -Recurse -Force
    }
    Expand-Archive -LiteralPath $CacheZip -DestinationPath $EmbedDir -Force

    $PthFile = Join-Path $EmbedDir "$PyTag._pth"
    if (-not (Test-Path -LiteralPath $PthFile)) {
        throw "${PyTag}._pth not found in embed package"
    }

    $sitePackages = Join-Path $EmbedDir 'Lib\site-packages'
    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
    @(
        "$PyTag.zip"
        '.'
        'Lib\site-packages'
        ''
        'import site'
    ) | Set-Content -LiteralPath $PthFile -Encoding ascii

    $GetPip = Join-Path $EmbedDir 'get-pip.py'
    Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $GetPip -UseBasicParsing

    if (-not (Test-Path -LiteralPath (Join-Path $EmbedDir 'python.exe'))) {
        throw 'python.exe missing after extract'
    }

    "Python $Version (Windows embeddable, 64-bit)" | Set-Content -LiteralPath (Join-Path $EmbedDir 'VERSION.txt') -Encoding UTF8
    Write-Host "OK: python-embed ($Version)"
}

Write-Host "Building student payload -> $WorkDir"
New-Item -ItemType Directory -Path (Split-Path -Parent $WorkDir) -Force | Out-Null

Copy-StudentPayload -Dest $WorkDir
Install-EmbedPython -TargetDir $WorkDir

foreach ($f in @('Install_once.bat', 'Start Structural Toolbox.bat')) {
    if (-not (Test-Path -LiteralPath (Join-Path $WorkDir $f))) {
        throw "missing required file: $f"
    }
}

$docsInPayload = Join-Path $WorkDir 'docs'
Get-ChildItem -LiteralPath $docsInPayload -File -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Name -like '*インストール*Windows.md') {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $WorkDir 'はじめ方_インストーラ版.md') -Force
    }
    elseif ($_.Name -like '*はじめ方*Windows.md' -and $_.Name -notlike '*インストール*') {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $WorkDir 'はじめ方_Windows.md') -Force
    }
}

if (-not $SkipZip) {
    if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
    Compress-Archive -Path $WorkDir -DestinationPath $ZipPath -Force
    $sizeMb = [math]::Round((Get-Item -LiteralPath $ZipPath).Length / 1MB, 1)
    Write-Host "ZIP: $ZipPath ($sizeMb MB)"
}

Write-Host ""
Write-Host "Payload folder: $WorkDir"
Write-Host "Next: .\student\build_student_installer.ps1 -SourceDir `"$WorkDir`""
