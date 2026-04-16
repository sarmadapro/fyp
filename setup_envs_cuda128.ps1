[CmdletBinding()]
param(
    [switch]$CreateVenvs,
    [switch]$InstallDeps,
    [switch]$InstallFrontend,
    [switch]$EnableSttGpu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-PythonVersion {
    Write-Step "Checking Python version"
    $pythonVersionRaw = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')").Trim()
    $pythonVersion = [Version]$pythonVersionRaw

    Write-Host "Python detected: $pythonVersionRaw"
    if ($pythonVersion -lt [Version]"3.10.0" -or $pythonVersion -ge [Version]"3.13.0") {
        throw "Use Python 3.10-3.12 for this project and CUDA wheels. Current: $pythonVersionRaw"
    }
}

function Assert-CudaCompatibility {
    Write-Step "Checking NVIDIA driver + CUDA compatibility"
    $smiOutput = & nvidia-smi 2>$null
    if (-not $smiOutput) {
        throw "nvidia-smi not found. Install/update NVIDIA driver first."
    }

    $cudaMatch = [regex]::Match(($smiOutput -join "`n"), "CUDA Version:\s*([0-9]+\.[0-9]+)")
    if (-not $cudaMatch.Success) {
        throw "Could not parse CUDA version from nvidia-smi."
    }

    $gpuLine = ($smiOutput | Select-String -Pattern "NVIDIA GeForce RTX 5070 Ti" | Select-Object -First 1)
    $cudaVersionText = $cudaMatch.Groups[1].Value
    $cudaVersion = [Version]$cudaVersionText

    Write-Host "CUDA reported by driver: $cudaVersionText"
    if (-not $gpuLine) {
        Write-Warning "RTX 5070 Ti was not detected in nvidia-smi output. Continue only if this is expected."
    }

    if ($cudaVersion -lt [Version]"12.8") {
        throw "CUDA $cudaVersionText is too old for your selected torch cu128 wheels. Update GPU driver first."
    }
}

function Assert-SttGpuDlls {
    Write-Step "Checking optional STT GPU runtime DLLs (CUDA 12 + cuDNN 9)"
    $dlls = @("cublas64_12.dll", "cudnn64_9.dll")
    foreach ($dll in $dlls) {
        $hit = & where.exe $dll 2>$null
        if (-not $hit) {
            throw "Missing $dll in PATH. Install CUDA 12 runtime + cuDNN 9 if you want STT on GPU."
        }
    }
}

function Ensure-Venv {
    param([string]$RelativeDir)
    $servicePath = Join-Path $ProjectRoot $RelativeDir
    $venvPath = Join-Path $servicePath "venv"

    if (-not (Test-Path $venvPath)) {
        Write-Step "Creating venv: $RelativeDir\venv"
        & python -m venv $venvPath
    } else {
        Write-Host "venv already exists: $RelativeDir\venv"
    }
}

function Install-PythonRequirements {
    param(
        [string]$RelativeDir,
        [bool]$InstallTorchCu128
    )

    $servicePath = Join-Path $ProjectRoot $RelativeDir
    $venvPython = Join-Path $servicePath "venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "venv missing for $RelativeDir. Run with -CreateVenvs first."
    }

    Write-Step "Upgrading pip/setuptools/wheel in $RelativeDir"
    & $venvPython -m pip install --upgrade pip setuptools wheel

    if ($InstallTorchCu128) {
        Write-Step "Installing torch stack (cu128) in $RelativeDir"
        & $venvPython -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
    }

    Write-Step "Installing requirements in $RelativeDir"
    & $venvPython -m pip install -r (Join-Path $servicePath "requirements.txt")

    if ($InstallTorchCu128) {
        Write-Step "Verifying torch CUDA in $RelativeDir"
        & $venvPython -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'cuda_available', torch.cuda.is_available())"
    }
}

function Print-ManualCommands {
    Write-Host ""
    Write-Host "Manual command list (PowerShell):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1) Preflight checks"
    Write-Host "   nvidia-smi"
    Write-Host "   python --version"
    Write-Host ""
    Write-Host "2) backend"
    Write-Host "   cd backend"
    Write-Host "   python -m venv venv"
    Write-Host "   .\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel"
    Write-Host "   .\venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128"
    Write-Host "   .\venv\Scripts\python.exe -m pip install -r requirements.txt"
    Write-Host ""
    Write-Host "3) services/stt"
    Write-Host "   cd ..\services\stt"
    Write-Host "   python -m venv venv"
    Write-Host "   .\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel"
    Write-Host "   .\venv\Scripts\python.exe -m pip install -r requirements.txt"
    Write-Host ""
    Write-Host "4) services/tts"
    Write-Host "   cd ..\tts"
    Write-Host "   python -m venv venv"
    Write-Host "   .\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel"
    Write-Host "   .\venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128"
    Write-Host "   .\venv\Scripts\python.exe -m pip install -r requirements.txt"
    Write-Host ""
    Write-Host "5) frontend"
    Write-Host "   cd ..\..\frontend"
    Write-Host "   npm install"
    Write-Host ""
    Write-Host "Optional STT GPU mode in .env"
    Write-Host "   STT_DEVICE=cuda"
    Write-Host "   STT_COMPUTE_TYPE=float16"
    Write-Host ""
    Write-Host "Script usage examples:"
    Write-Host "   .\setup_envs_cuda128.ps1"
    Write-Host "   .\setup_envs_cuda128.ps1 -CreateVenvs"
    Write-Host "   .\setup_envs_cuda128.ps1 -CreateVenvs -InstallDeps -InstallFrontend"
    Write-Host "   .\setup_envs_cuda128.ps1 -CreateVenvs -InstallDeps -EnableSttGpu"
}

Assert-PythonVersion
Assert-CudaCompatibility
if ($EnableSttGpu) {
    Assert-SttGpuDlls
}

if ($CreateVenvs) {
    Ensure-Venv "backend"
    Ensure-Venv "services\stt"
    Ensure-Venv "services\tts"
}

if ($InstallDeps) {
    Install-PythonRequirements -RelativeDir "backend" -InstallTorchCu128 $true
    Install-PythonRequirements -RelativeDir "services\stt" -InstallTorchCu128 $false
    Install-PythonRequirements -RelativeDir "services\tts" -InstallTorchCu128 $true
}

if ($InstallFrontend) {
    Write-Step "Installing frontend dependencies"
    & npm install --prefix (Join-Path $ProjectRoot "frontend")
}

if (-not $CreateVenvs -and -not $InstallDeps -and -not $InstallFrontend) {
    Print-ManualCommands
}
