# Runs the tests and produces dist\AltyaziIndirici.exe
# Native tools write progress to stderr, so failures are detected by exit code.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

function Check($step) {
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $step"; exit 1 }
}

if (-not (Test-Path .venv\Scripts\python.exe)) { python -m venv .venv; Check 'venv' }
$py = (Resolve-Path .venv\Scripts\python.exe).Path

& $py -m pip install -q -r requirements.txt
Check 'dependencies'

& $py -m unittest discover -s tests
Check 'tests'

New-Item -ItemType Directory -Force build | Out-Null
& $py tools\make_icon.py build\app.ico
Check 'icon'

& $py -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name AltyaziIndirici --icon build\app.ico `
  --paths src `
  --add-data "src\altyazi\web;altyazi\web" `
  --collect-all yt_dlp_ejs `
  --collect-submodules yt_dlp `
  --hidden-import clr `
  run_app.py
Check 'pyinstaller'

Get-Item dist\AltyaziIndirici.exe | Select-Object FullName, Length
