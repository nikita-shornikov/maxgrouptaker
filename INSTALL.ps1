# INSTALL.ps1 — установка MAX Group Taker
# Запускать правой кнопкой -> "Выполнить с помощью PowerShell"

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Версия Python для скачивания если winget недоступен
$PYTHON_VERSION = "3.12.8"
$PYTHON_URL     = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"

function Write-OK   { param($msg) Write-Host "  OK: $msg" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "  ОШИБКА: $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  $msg" -ForegroundColor Gray }

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "   Установка MAX Group Taker" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# -------------------------------------------------------
# Функция: найти рабочий python 3.10+
# -------------------------------------------------------
function Find-Python {
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)") {
                if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 10) {
                    return $cmd
                }
            }
        } catch {}
    }
    return $null
}

# -------------------------------------------------------
# Функция: обновить PATH в текущей сессии
# -------------------------------------------------------
function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
}

# -------------------------------------------------------
# Функция: установить Python автоматически
# -------------------------------------------------------
function Install-Python {
    # Способ 1 — winget (встроен в Windows 10/11)
    Write-Info "Пробуем установить через winget..."
    try {
        $wg = Get-Command winget -ErrorAction Stop
        & winget install --id Python.Python.3.12 `
            --source winget `
            --accept-package-agreements `
            --accept-source-agreements `
            --silent
        Refresh-Path
        if (Find-Python) { return $true }
    } catch {
        Write-Info "winget недоступен, переходим к прямой загрузке..."
    }

    # Способ 2 — скачать установщик с python.org
    Write-Info "Скачиваем Python $PYTHON_VERSION с python.org..."
    $installer = Join-Path $env:TEMP "python-installer.exe"
    try {
        Invoke-WebRequest -Uri $PYTHON_URL -OutFile $installer -UseBasicParsing
    } catch {
        Write-Fail "Не удалось скачать Python. Проверь интернет-соединение."
        return $false
    }

    Write-Info "Устанавливаем Python (тихая установка)..."
    # /quiet       — без окон
    # PrependPath  — добавить в PATH
    # InstallAllUsers=0 — только для текущего пользователя (не нужны права админа)
    $proc = Start-Process -FilePath $installer `
        -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0" `
        -Wait -PassThru
    Remove-Item $installer -Force -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-Fail "Установщик Python завершился с кодом $($proc.ExitCode)"
        return $false
    }

    Refresh-Path
    return $true
}

# -------------------------------------------------------
# ШАГ 1 — Python
# -------------------------------------------------------
Write-Host "[1/5] Проверка Python..." -ForegroundColor White
$pythonCmd = Find-Python

if ($pythonCmd) {
    $ver = & $pythonCmd --version 2>&1
    Write-OK $ver
} else {
    Write-Info "Python 3.10+ не найден. Устанавливаем автоматически..."
    Write-Host ""

    $ok = Install-Python
    if (-not $ok) {
        Write-Host ""
        Write-Fail "Не удалось установить Python автоматически."
        Write-Host ""
        Write-Host "  Установи вручную:" -ForegroundColor White
        Write-Host "  1. Открой https://www.python.org/downloads/" -ForegroundColor White
        Write-Host "  2. Скачай Python 3.12 и установи" -ForegroundColor White
        Write-Host "  3. Поставь галочку 'Add Python to PATH'" -ForegroundColor White
        Write-Host "  4. Запусти INSTALL.ps1 снова" -ForegroundColor White
        Write-Host ""
        Read-Host "Нажми Enter для выхода"
        exit 1
    }

    $pythonCmd = Find-Python
    if (-not $pythonCmd) {
        Write-Fail "Python установлен, но не виден в PATH. Перезапусти INSTALL.ps1."
        Read-Host "Нажми Enter для выхода"
        exit 1
    }

    $ver = & $pythonCmd --version 2>&1
    Write-OK "Python установлен: $ver"
}

# -------------------------------------------------------
# ШАГ 2 — Виртуальное окружение
# -------------------------------------------------------
Write-Host "[2/5] Создание виртуального окружения..." -ForegroundColor White
$venvPath = Join-Path $scriptDir ".venv"
if (Test-Path $venvPath) {
    Write-Info "Уже существует, пропускаем"
} else {
    & $pythonCmd -m venv $venvPath
    Write-OK "создано в .venv"
}

$pip        = Join-Path $venvPath "Scripts\pip.exe"
$playwright = Join-Path $venvPath "Scripts\playwright.exe"

# -------------------------------------------------------
# ШАГ 3 — Зависимости
# -------------------------------------------------------
Write-Host "[3/5] Установка зависимостей..." -ForegroundColor White
& $pip install --upgrade pip --quiet
& $pip install -r (Join-Path $scriptDir "requirements.txt") --quiet
Write-OK "все пакеты установлены"

# -------------------------------------------------------
# ШАГ 4 — Браузер Chromium
# -------------------------------------------------------
Write-Host "[4/5] Установка браузера Chromium..." -ForegroundColor White
Write-Info "Может занять 2-5 минут, скачивается один раз"
& $playwright install chromium
Write-OK "Chromium установлен"

# -------------------------------------------------------
# ШАГ 5 — Конфиг и ярлык
# -------------------------------------------------------
Write-Host "[5/5] Финальная настройка..." -ForegroundColor White

$configDst = Join-Path $scriptDir "config.yaml"
$configSrc = Join-Path $scriptDir "config.example.yaml"
if (-not (Test-Path $configDst)) {
    Copy-Item $configSrc $configDst
    Write-OK "config.yaml создан"
} else {
    Write-Info "config.yaml уже есть"
}

$batPath    = Join-Path $scriptDir "MAX GroupTaker.bat"
$batContent = "@echo off`r`ncd /d `"%~dp0`"`r`npowershell -ExecutionPolicy RemoteSigned -File `"%~dp0run.ps1`"`r`npause"
[System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::ASCII)
Write-OK "файл запуска создан"

try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shell   = New-Object -ComObject WScript.Shell
    $lnk     = $shell.CreateShortcut((Join-Path $desktop "MAX GroupTaker.lnk"))
    $lnk.TargetPath       = $batPath
    $lnk.WorkingDirectory = $scriptDir
    $lnk.Description      = "MAX Group Taker"
    $lnk.Save()
    Write-OK "ярлык создан на рабочем столе"
} catch {
    Write-Info "Ярлык не создан автоматически — запускай через MAX GroupTaker.bat"
}

# -------------------------------------------------------
# ГОТОВО
# -------------------------------------------------------
Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "   Установка завершена успешно!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
Write-Host "  На рабочем столе появился ярлык 'MAX GroupTaker'" -ForegroundColor White
Write-Host "  Дважды кликни на него чтобы запустить программу." -ForegroundColor White
Write-Host ""
Read-Host "Нажми Enter для выхода"
