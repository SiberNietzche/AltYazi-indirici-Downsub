# Runs the tests, packages the Python engine as a sidecar and builds the Tauri app.
# Output: src-tauri\target\release\altyazi-indirici.exe and an installer under
# src-tauri\target\release\bundle\nsis. Pass -NoBundle to skip the installer.
# Requires Python 3.11, Rust (MSVC toolchain) and Node.js; WebView2 Runtime at run time.
param([switch]$NoBundle)

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

# The window icon and the emblem mask come from the same drawing.
New-Item -ItemType Directory -Force src-tauri\icons, src-tauri\binaries | Out-Null
& $py tools\make_icon.py src-tauri\icons\icon.ico src\altyazi\web\laurel.svg
Check 'icon'

# Keep this machine's user folder out of the binaries: the Rust compiler otherwise embeds
# full source paths (C:\Users\<name>\...) in the program.
$env:CARGO_ENCODED_RUSTFLAGS = "--remap-path-prefix=$env:USERPROFILE=~"

# Tauri expects the sidecar to carry the Rust target triple in its file name.
$triple = (& rustc -vV | Select-String '^host: ').ToString().Substring(6).Trim()
Check 'rustc'

# The engine is a console program so that its stdin pipe exists: it exits when the shell closes it.
& $py -m PyInstaller --noconfirm --clean --onefile --console `
  --name altyazi-server `
  --distpath build\sidecar --workpath build\sidecar-work --specpath build `
  --paths src `
  --add-data "$PSScriptRoot\src\altyazi\web;altyazi\web" `
  --collect-all yt_dlp_ejs `
  --collect-submodules yt_dlp `
  run_app.py
Check 'pyinstaller'
Copy-Item build\sidecar\altyazi-server.exe "src-tauri\binaries\altyazi-server-$triple.exe" -Force

if ($NoBundle) {
    & cargo build --release --manifest-path src-tauri\Cargo.toml
    Check 'cargo'
} else {
    Push-Location src-tauri
    & npx --yes "@tauri-apps/cli@2" build
    $failed = $LASTEXITCODE -ne 0
    Pop-Location
    if ($failed) { Write-Host 'FAILED: tauri build'; exit 1 }
    Get-ChildItem src-tauri\target\release\bundle\nsis\*.exe | Select-Object FullName, Length
}

Get-Item src-tauri\target\release\altyazi-indirici.exe |
  Select-Object FullName, Length
