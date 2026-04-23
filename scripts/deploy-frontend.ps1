# Deploy Frontend to Cloudflare Pages
#
# Usage:
#   .\scripts\deploy-frontend.ps1
#   .\scripts\deploy-frontend.ps1 -ProjectName latextrans-preview
#   .\scripts\deploy-frontend.ps1 -Branch main
#   .\scripts\deploy-frontend.ps1 -AllowPreview
#   .\scripts\deploy-frontend.ps1 -SkipPreflight
#
# The API URL is read from frontend/.env.production by default.

param(
    [string]$ProjectName = "latextrans",
    [string]$Branch,
    [switch]$AllowPreview,
    [switch]$SkipInstall,
    [switch]$SkipBuild,
    [switch]$SkipDeploy,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$FrontendDir = Join-Path $PSScriptRoot "..\frontend"
$EnvFile = Join-Path $FrontendDir ".env.production"
$ApiBaseUrl = $null

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-WarnLine([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrorLine([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @(),
        [Parameter(Mandatory = $true)][string]$StepName
    )

    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE."
    }
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Name=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return ($line -replace "^\s*$Name=", "").Trim()
}

function Get-OptionalCommandOutput {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @()
    )

    try {
        $output = & $FilePath @ArgumentList 2>$null
        if ($LASTEXITCODE -ne 0) {
            return $null
        }

        return ($output | Out-String).Trim()
    }
    catch {
        return $null
    }
}

function Get-GitBranchName {
    return Get-OptionalCommandOutput -FilePath "git" -ArgumentList @("branch", "--show-current")
}

function Get-DefaultRemoteBranch {
    $symbolicRef = Get-OptionalCommandOutput -FilePath "git" -ArgumentList @("symbolic-ref", "refs/remotes/origin/HEAD")
    if (-not $symbolicRef) {
        return "main"
    }

    return ($symbolicRef -split "/")[-1]
}

$ApiBaseUrl = Get-EnvValue -Path $EnvFile -Name "VITE_API_BASE_URL"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  LaTeXTrans - Frontend Deployment to Cloudflare" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$wrangler = Get-Command wrangler -ErrorAction SilentlyContinue
if (-not $wrangler) {
    Write-WarnLine "Wrangler CLI not found. Installing it globally..."
    Invoke-CheckedCommand -FilePath "npm" -ArgumentList @("install", "-g", "wrangler") -StepName "Wrangler installation"
    $wrangler = Get-Command wrangler -ErrorAction SilentlyContinue
    if (-not $wrangler) {
        throw "Wrangler installation completed, but the wrangler command is still unavailable in PATH."
    }
}

Push-Location $FrontendDir

try {
    $currentGitBranch = Get-GitBranchName
    $defaultGitBranch = Get-DefaultRemoteBranch

    if (-not $Branch) {
        $Branch = if ($currentGitBranch) { $currentGitBranch } else { $defaultGitBranch }
    }

    if ($currentGitBranch) {
        Write-Info "Current git branch: $currentGitBranch"
    } else {
        Write-WarnLine "Unable to determine current git branch. Falling back to Pages branch '$Branch'."
    }
    Write-Info "Cloudflare Pages branch target: $Branch"

    if ($ProjectName -eq "latextrans" -and $Branch -ne $defaultGitBranch) {
        $previewMessage = "Cloudflare Pages branch '$Branch' is a preview deployment and will not update the production custom domain. Use -Branch $defaultGitBranch for production, or rerun with -AllowPreview if you intentionally want a preview deployment."
        if (-not $AllowPreview) {
            throw $previewMessage
        }

        Write-WarnLine $previewMessage
    }

    if ($ApiBaseUrl) {
        Write-Info "API URL from .env.production: $ApiBaseUrl"
        if ($ApiBaseUrl -match '/api/?$') {
            Write-WarnLine "VITE_API_BASE_URL usually should not include a trailing /api in this project."
        }
    } else {
        Write-WarnLine "VITE_API_BASE_URL not found in .env.production. Build will use whatever Vite env resolves at build time."
    }

    if (-not $SkipPreflight) {
        Write-Info "Running Wrangler preflight (auth + network)..."
        Invoke-CheckedCommand -FilePath "wrangler" -ArgumentList @("whoami") -StepName "Wrangler preflight"
    } else {
        Write-WarnLine "Skipping Wrangler preflight checks."
    }

    if (-not $SkipInstall -and -not (Test-Path "node_modules")) {
        Write-Info "Installing dependencies..."
        Invoke-CheckedCommand -FilePath "npm" -ArgumentList @("install") -StepName "Dependency installation"
    } elseif (-not (Test-Path "node_modules")) {
        throw "node_modules is missing, but -SkipInstall was provided."
    }

    if (-not $SkipBuild) {
        Write-Info "Building frontend..."
        Invoke-CheckedCommand -FilePath "npm" -ArgumentList @("run", "build") -StepName "Frontend build"
    } else {
        Write-WarnLine "Skipping frontend build."
    }

    if (-not (Test-Path "dist")) {
        throw "Build output folder 'dist' was not found."
    }

    if (-not $SkipDeploy) {
        Write-Info "Deploying to Cloudflare Pages project '$ProjectName' on branch '$Branch'..."
        Write-Host ""
        Invoke-CheckedCommand -FilePath "wrangler" -ArgumentList @("pages", "deploy", "dist", "--project-name", $ProjectName, "--branch", $Branch) -StepName "Cloudflare Pages deploy"
    } else {
        Write-WarnLine "Skipping Cloudflare deploy."
    }

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  Deployment Complete!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify the new deployment in Cloudflare Pages and confirm it points to your current API domain." -ForegroundColor Cyan
}
catch {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Red
    Write-Host "  Deployment Failed" -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    Write-ErrorLine $_.Exception.Message
    exit 1
}
finally {
    Pop-Location
}
