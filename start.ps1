$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

# Source: requires-python in pyproject.toml.
$MinimumPythonMajor = 3
$MinimumPythonMinor = 12
$Entrypoint = "app/app.py"
$VenvPython = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"

function Stop-LeadPulse {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Message,
        [int]$ExitCode = 1
    )

    foreach ($line in $Message) {
        Write-Host $line
    }
    exit $ExitCode
}

function Invoke-NativeQuiet {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [string[]]$Arguments = @()
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 can promote redirected native stderr to an error record.
        $ErrorActionPreference = "Continue"
        & $Command @Arguments *> $null
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Invoke-NativeCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [string[]]$Arguments = @()
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $Command @Arguments 2>$null)
        return [PSCustomObject]@{
            ExitCode = $LASTEXITCODE
            Output = $output
        }
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Show-AnalyticsInstructions {
    Write-Host "[LeadPulse] A camada analítica ainda não está disponível."
    Write-Host ""
    Write-Host "Este projeto utiliza datasets públicos da Olist que não são versionados no Git."
    Write-Host ""
    Write-Host "Para a primeira execução:"
    Write-Host "1. obtenha os datasets conforme docs/data/source-contracts.md;"
    Write-Host "2. coloque os arquivos na estrutura data/raw indicada no README;"
    Write-Host "3. execute as ingestões documentadas no README;"
    Write-Host "4. execute dbt run;"
    Write-Host "5. execute novamente start.ps1."
}

Write-Host "[LeadPulse] Verificando Python..."
$pythonCandidates = @(
    [PSCustomObject]@{ Command = "py"; Arguments = @("-3") },
    [PSCustomObject]@{ Command = "python"; Arguments = @() },
    [PSCustomObject]@{ Command = "python3"; Arguments = @() }
)
$selectedPython = $null
$foundPython = $false

foreach ($candidate in $pythonCandidates) {
    $commandInfo = Get-Command $candidate.Command -ErrorAction SilentlyContinue
    if ($null -eq $commandInfo) {
        continue
    }

    # Windows Store aliases are placeholders, not usable Python installations.
    if ($commandInfo.Source -like "*\WindowsApps\python*.exe") {
        continue
    }

    $candidateCommand = $candidate.Command
    $candidateArguments = @($candidate.Arguments)
    try {
        $version = & $candidateCommand @candidateArguments -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        $versionExitCode = $LASTEXITCODE
    }
    catch {
        continue
    }

    if ($versionExitCode -ne 0 -or [string]::IsNullOrWhiteSpace("$version")) {
        continue
    }

    $foundPython = $true
    $parts = "$version".Trim().Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -gt $MinimumPythonMajor -or
        ($major -eq $MinimumPythonMajor -and $minor -ge $MinimumPythonMinor)) {
        $selectedPython = $candidate
        break
    }
}

if ($null -eq $selectedPython) {
    if ($foundPython) {
        Stop-LeadPulse @(
            "[LeadPulse] A versão instalada do Python não é compatível.",
            "Versão mínima necessária: $MinimumPythonMajor.$MinimumPythonMinor"
        )
    }
    Stop-LeadPulse @(
        "[LeadPulse] Python compatível não foi encontrado.",
        "Instale a versão mínima indicada no README e execute novamente."
    )
}

Write-Host "[LeadPulse] Preparando ambiente virtual..."
if (-not (Test-Path -LiteralPath ".venv" -PathType Container)) {
    $selectedCommand = $selectedPython.Command
    $selectedArguments = @($selectedPython.Arguments)
    & $selectedCommand @selectedArguments -m venv ".venv"
    if ($LASTEXITCODE -ne 0) {
        Stop-LeadPulse "[LeadPulse] Não foi possível criar o ambiente virtual."
    }
}

if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    Stop-LeadPulse @(
        "[LeadPulse] A pasta .venv existe, mas o Python do ambiente virtual não foi encontrado.",
        "Remova ou corrija a .venv manualmente e execute novamente."
    )
}

& $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info >= ($MinimumPythonMajor, $MinimumPythonMinor) else 1)"
if ($LASTEXITCODE -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] O Python da .venv não é compatível.",
        "Versão mínima necessária: $MinimumPythonMajor.$MinimumPythonMinor",
        "Corrija a .venv manualmente e execute novamente."
    )
}

Write-Host "[LeadPulse] Sincronizando dependências..."
& $VenvPython -m pip install -e ".[dev,data,dashboard]"
if ($LASTEXITCODE -ne 0) {
    Stop-LeadPulse "[LeadPulse] Não foi possível instalar as dependências do projeto."
}

Write-Host "[LeadPulse] Verificando configuração..."
if (-not (Test-Path -LiteralPath ".env" -PathType Leaf)) {
    if (-not (Test-Path -LiteralPath ".env.example" -PathType Leaf)) {
        Stop-LeadPulse @(
            "[LeadPulse] Arquivo .env não encontrado.",
            "[LeadPulse] O arquivo .env.example também não existe. Restaure-o e execute novamente."
        )
    }
    Write-Host "[LeadPulse] Arquivo .env não encontrado."
    Write-Host "[LeadPulse] Criando .env a partir de .env.example..."
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

Write-Host "[LeadPulse] Verificando Docker..."
if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-LeadPulse @(
        "[LeadPulse] Docker não foi encontrado.",
        "Instale Docker Desktop e execute novamente."
    )
}

$dockerVersionExitCode = Invoke-NativeQuiet -Command "docker" -Arguments @("--version")
if ($dockerVersionExitCode -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] Docker não foi encontrado.",
        "Instale Docker Desktop e execute novamente."
    )
}

$dockerInfoExitCode = Invoke-NativeQuiet -Command "docker" -Arguments @("info")
if ($dockerInfoExitCode -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] Docker está instalado, mas o daemon não está disponível.",
        "Inicie o Docker Desktop e execute novamente."
    )
}

$composeVersionExitCode = Invoke-NativeQuiet -Command "docker" -Arguments @(
    "compose", "version"
)
if ($composeVersionExitCode -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] Docker Compose não está disponível.",
        "Instale uma versão do Docker com Compose e execute novamente."
    )
}

Write-Host "[LeadPulse] Iniciando PostgreSQL..."
& docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Stop-LeadPulse "[LeadPulse] Não foi possível iniciar o PostgreSQL com Docker Compose."
}

Write-Host "[LeadPulse] Aguardando banco de dados..."
$healthDeadline = [DateTime]::UtcNow.AddSeconds(60)
$postgresReady = $false
while ([DateTime]::UtcNow -lt $healthDeadline) {
    $composePs = Invoke-NativeCapture -Command "docker" -Arguments @(
        "compose", "ps", "-q", "postgres"
    )
    $containerId = ($composePs.Output | Select-Object -First 1)
    if (-not [string]::IsNullOrWhiteSpace("$containerId")) {
        $inspect = Invoke-NativeCapture -Command "docker" -Arguments @(
            "inspect",
            "--format",
            '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}',
            "$containerId"
        )
        $healthStatus = ($inspect.Output | Select-Object -First 1)
        if ("$healthStatus".Trim() -eq "healthy") {
            $postgresReady = $true
            break
        }
    }
    Start-Sleep -Seconds 2
}

if (-not $postgresReady) {
    Stop-LeadPulse @(
        "[LeadPulse] PostgreSQL não ficou disponível dentro do tempo esperado.",
        "Verifique:",
        "docker compose ps",
        "docker compose logs postgres"
    )
}
Write-Host "[LeadPulse] PostgreSQL disponível."

Write-Host "[LeadPulse] Verificando camada analítica..."
$analyticsCheck = @'
import sys

import psycopg

from leadpulse.config import PostgresConfig

MARTS = (
    "analytics.mart_acquisition_performance",
    "analytics.mart_seller_activation",
    "analytics.mart_marketing_efficiency",
    "analytics.mart_downstream_performance",
)

try:
    config = PostgresConfig.from_env()
    with psycopg.connect(
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        connect_timeout=5,
        options="-c default_transaction_read_only=on",
    ) as connection:
        with connection.cursor() as cursor:
            missing = []
            for mart in MARTS:
                cursor.execute("SELECT to_regclass(%s)", (mart,))
                if cursor.fetchone()[0] is None:
                    missing.append(mart)
except Exception:
    raise SystemExit(2)

raise SystemExit(3 if missing else 0)
'@

$analyticsCheck | & $VenvPython -
$analyticsExitCode = $LASTEXITCODE
if ($analyticsExitCode -eq 3) {
    Show-AnalyticsInstructions
    exit 0
}
if ($analyticsExitCode -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] Não foi possível verificar a camada analítica.",
        "Confirme a configuração do banco em .env e tente novamente."
    )
}

Write-Host "[LeadPulse] Validando Streamlit..."
$streamlitExitCode = Invoke-NativeQuiet -Command $VenvPython -Arguments @(
    "-m", "streamlit", "--version"
)
if ($streamlitExitCode -ne 0) {
    Stop-LeadPulse @(
        "[LeadPulse] Streamlit não está disponível no ambiente virtual.",
        "Tente reinstalar as dependências:",
        'python -m pip install -e ".[dev,data,dashboard]"'
    )
}

if (-not (Test-Path -LiteralPath $Entrypoint -PathType Leaf)) {
    Stop-LeadPulse "[LeadPulse] O entrypoint do dashboard não foi encontrado."
}

Write-Host "[LeadPulse] Iniciando dashboard..."
Write-Host "[LeadPulse] URL: http://localhost:8501"
& $VenvPython -m streamlit run $Entrypoint --server.port 8501
exit $LASTEXITCODE
