# Deploy Frontend to Cloudflare Pages
# 
# Usage: .\scripts\deploy-frontend.ps1 [-TunnelUrl <url>]
# 
# Parameters:
#   -TunnelUrl: Optional. The Cloudflare Tunnel URL for the backend API
#               If not provided, you'll need to set VITE_API_URL manually before building

param(
    [string]$TunnelUrl = ""
)

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
    # Set environment variable if TunnelUrl provided
    if ($TunnelUrl -ne "") {
        Write-Host "[INFO] Setting API URL to: $TunnelUrl/api" -ForegroundColor Green
        $envContent = "VITE_API_URL=$TunnelUrl/api"
        Set-Content -Path ".env.production" -Value $envContent
    } else {
        if (-not (Test-Path ".env.production")) {
            Write-Host "[WARNING] No .env.production file found!" -ForegroundColor Yellow
            Write-Host "  Please create .env.production with VITE_API_URL set to your Tunnel URL" -ForegroundColor Yellow
            Write-Host "  Example: VITE_API_URL=https://xxx-xxx.trycloudflare.com/api" -ForegroundColor Yellow
            Write-Host ""
        }
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
    Write-Host "Your frontend is now live on Cloudflare Pages." -ForegroundColor Cyan
    Write-Host "Make sure your backend is running and Tunnel is active!" -ForegroundColor Cyan

} finally {
    Pop-Location
}
