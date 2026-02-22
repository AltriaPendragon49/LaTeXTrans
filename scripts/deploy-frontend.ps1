# Deploy Frontend to Cloudflare Pages
# 
# Usage: .\scripts\deploy-frontend.ps1
#
# The API URL is now fixed (api.latextrans.online) and configured in .env.production,
# so no parameters are needed.

$ErrorActionPreference = "Stop"
$FrontendDir = Join-Path $PSScriptRoot "..\frontend"

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
    Write-Host "[INFO] API URL: https://api.latextrans.online/api (from .env.production)" -ForegroundColor Green

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
    Write-Host "Your frontend is now live at:" -ForegroundColor Cyan
    Write-Host "  https://latextrans.online" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Make sure your backend and tunnel are running!" -ForegroundColor Cyan

} finally {
    Pop-Location
}
