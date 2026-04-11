# Deploy Frontend to Cloudflare Pages
# 
# Usage: .\scripts\deploy-frontend.ps1
#
# The API URL is read from frontend/.env.production,
# so no parameters are needed.

$ErrorActionPreference = "Stop"
$FrontendDir = Join-Path $PSScriptRoot "..\frontend"
$EnvFile = Join-Path $FrontendDir ".env.production"
$ApiBaseUrl = $null

if (Test-Path $EnvFile) {
    $ApiLine = Get-Content $EnvFile | Where-Object { $_ -match '^\s*VITE_API_BASE_URL=' } | Select-Object -First 1
    if ($ApiLine) {
        $ApiBaseUrl = ($ApiLine -replace '^\s*VITE_API_BASE_URL=', '').Trim()
    }
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  LaTeXTrans - Frontend Deployment to Cloudflare" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if wrangler is installed
$wrangler = Get-Command wrangler -ErrorAction SilentlyContinue
if (-not $wrangler) {
    Write-Host "[INFO] Installing Wrangler CLI..." -ForegroundColor Yellow
    npm install -g wrangler
}

# Navigate to frontend directory
Push-Location $FrontendDir

try {
    if ($ApiBaseUrl) {
        Write-Host "[INFO] API URL from .env.production: $ApiBaseUrl" -ForegroundColor Green
        if ($ApiBaseUrl -match '/api/?$') {
            Write-Host "[WARN] VITE_API_BASE_URL usually should not include a trailing /api in this project." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARN] VITE_API_BASE_URL not found in .env.production. Build will use whatever Vite env resolves at build time." -ForegroundColor Yellow
    }

    # Install dependencies if needed
    if (-not (Test-Path "node_modules")) {
        Write-Host "[INFO] Installing dependencies..." -ForegroundColor Green
        npm install
    }

    # Build the frontend
    Write-Host "[INFO] Building frontend..." -ForegroundColor Green
    npm run build

    if (-not (Test-Path "dist")) {
        Write-Host "[ERROR] Build failed - dist folder not found!" -ForegroundColor Red
        exit 1
    }

    # Deploy to Cloudflare Pages
    Write-Host "[INFO] Deploying to Cloudflare Pages..." -ForegroundColor Green
    Write-Host ""
    wrangler pages deploy dist --project-name latextrans

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  Deployment Complete!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify the new deployment in Cloudflare Pages and confirm it points to your current API domain." -ForegroundColor Cyan

} finally {
    Pop-Location
}
