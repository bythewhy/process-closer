$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$localPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $localPython) {
    $localPython
} else {
    (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}
if (-not $python) {
    throw "Python 3 не найден в PATH"
}

Set-Location $root
& $python -m PyInstaller --clean --noconfirm --name process-closer --paths src src\process_closer\launcher.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$version = "1.0.0"
$release = Join-Path $root "release\process-closer-$version-windows"
$archive = Join-Path $root "release\process-closer-$version-windows.zip"
New-Item -ItemType Directory -Force -Path $release | Out-Null
Copy-Item -Path (Join-Path $root "dist\process-closer\*") -Destination $release -Recurse -Force
Copy-Item -LiteralPath (Join-Path $root "main.py") -Destination $release -Force
Copy-Item -LiteralPath (Join-Path $root "README.md") -Destination $release -Force
Copy-Item -LiteralPath (Join-Path $root "RELEASE.md") -Destination $release -Force
Copy-Item -LiteralPath (Join-Path $root "LICENSE") -Destination $release -Force
if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive -Force
}
Compress-Archive -Path (Join-Path $release "*") -DestinationPath $archive
Write-Output "Готово: $archive"
