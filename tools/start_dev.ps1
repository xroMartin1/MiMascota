param(
    [switch]$PrepareOnly,
    [switch]$IgnoreProjectVenv,
    [string]$RuntimeHome = ""
)

$ErrorActionPreference = "Stop"
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$requirements = Join-Path $project "requirements.txt"
$program = Join-Path $project "main.py"
$projectPython = Join-Path $project ".venv\Scripts\python.exe"
$checkScript = Join-Path $PSScriptRoot "check_runtime.py"

function Test-Runtime([string]$pythonPath) {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { return $false }
    try {
        & $pythonPath $checkScript 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-BasePython {
    if ($env:PETCARE_PYTHON -and (Test-Path -LiteralPath $env:PETCARE_PYTHON -PathType Leaf)) {
        try {
            & $env:PETCARE_PYTHON -c 'import sys; assert sys.version_info[:2] in ((3, 11), (3, 12))' 2>$null
            if ($LASTEXITCODE -eq 0) { return $env:PETCARE_PYTHON }
        } catch { }
    }
    $candidates = @(
        @{ Command = "py"; Arguments = @("-3.12") },
        @{ Command = "py"; Arguments = @("-3.11") },
        @{ Command = "python"; Arguments = @() }
    )
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $command -or $command.Source -like "*WindowsApps*") { continue }
        $arguments = $candidate.Arguments
        try {
            $resolved = & $candidate.Command @arguments -c 'import sys; assert sys.version_info[:2] in ((3, 11), (3, 12)); print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved) { return ($resolved | Select-Object -Last 1).Trim() }
        } catch { }
    }
    return $null
}

try {
    if (-not (Test-Path -LiteralPath $program -PathType Leaf) -or
        -not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
        throw "Faltan main.py o requirements.txt. Copia el proyecto completo."
    }

    $pythonPath = $null
    if (-not $IgnoreProjectVenv -and (Test-Runtime $projectPython)) {
        $pythonPath = $projectPython
        Write-Host "Usando el entorno de desarrollo de esta PC."
    } else {
        if (Test-Path -LiteralPath $projectPython) {
            Write-Host "El entorno copiado no funciona en esta PC. Preparando uno local..."
        }
        $basePython = Find-BasePython
        if (-not $basePython) {
            throw "Instala Python 3.12 o 3.11 para Windows y vuelve a abrir este archivo. Marca la opcion Add Python to PATH o instala el lanzador py."
        }
        if (-not $RuntimeHome) {
            if (-not $env:LOCALAPPDATA) { throw "No se encontro LOCALAPPDATA para crear el entorno." }
            $RuntimeHome = Join-Path $env:LOCALAPPDATA "PetCareApp"
        }
        New-Item -ItemType Directory -Path $RuntimeHome -Force | Out-Null
        $runtime = Join-Path $RuntimeHome "dev-venv"
        $pythonPath = Join-Path $runtime "Scripts\python.exe"
        $marker = Join-Path $runtime ".requirements.sha256"
        if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
            Write-Host "Creando un entorno de Python en: $runtime"
            & $basePython -m venv $runtime
            if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno de Python." }
        } else {
            # --upgrade reescribe pyvenv.cfg si la instalacion base de Python cambio de ruta.
            & $pythonPath -c 'import sys; print(sys.version)' 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Reparando el entorno local..."
                & $basePython -m venv --upgrade $runtime
                if ($LASTEXITCODE -ne 0) { throw "No se pudo reparar el entorno local: $runtime" }
            }
        }
        $requiredHash = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
        $installedHash = if (Test-Path -LiteralPath $marker -PathType Leaf) {
            (Get-Content -LiteralPath $marker -Raw).Trim()
        } else { "" }
        if ($installedHash -ne $requiredHash -or -not (Test-Runtime $pythonPath)) {
            Write-Host "Instalando dependencias (solo la primera vez o cuando cambien)..."
            & $pythonPath -m pip install --disable-pip-version-check -r $requirements
            if ($LASTEXITCODE -ne 0 -or -not (Test-Runtime $pythonPath)) {
                throw "No se pudieron instalar Kivy y KivyMD. Revisa tu conexion a internet y vuelve a intentar."
            }
            Set-Content -LiteralPath $marker -Value $requiredHash -Encoding ASCII -NoNewline
        }
    }

    if ($PrepareOnly) {
        Write-Host "Entorno listo: $pythonPath"
        exit 0
    }
    Set-Location -LiteralPath $project
    & $pythonPath $program
    exit $LASTEXITCODE
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
