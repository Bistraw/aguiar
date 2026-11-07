# Builds the portable executable: dist\InterviewAssistant.exe
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}

Write-Host "Installing dependencies..."
& $python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

Write-Host "Building executable..."
$schema = Join-Path $PSScriptRoot "schema.sql"
$assets = Join-Path $PSScriptRoot "assets"
& $python -m PyInstaller `
    --noconfirm --clean `
    --onefile --windowed `
    --name InterviewAssistant `
    --icon (Join-Path $assets "app.ico") `
    --add-data "$schema;." `
    --add-data "$assets;assets" `
    --distpath dist --workpath build --specpath build `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

Write-Host "Done: $(Join-Path $PSScriptRoot 'dist\InterviewAssistant.exe')"
Write-Host "db.sqlite is created next to the .exe on first run."
