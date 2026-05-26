# MAX Group Taker - launcher

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host ""
Write-Host "=== MAX Group Taker ===" -ForegroundColor Cyan
Write-Host ""

$chatId = Read-Host "ID gruppy ili ssylka (napr: https://max.ru/join/TOKEN)"
if (-not $chatId) { Write-Host "Error: chat-id ne ukazan" -ForegroundColor Red; exit 1 }

$name = Read-Host "Imya dlya poiska (napr: Ivan)"
if (-not $name) { Write-Host "Error: imya ne ukazano" -ForegroundColor Red; exit 1 }

Write-Host ""
& $python (Join-Path $PSScriptRoot "script2_web_add_to_group.py") --chat-id $chatId --name $name
