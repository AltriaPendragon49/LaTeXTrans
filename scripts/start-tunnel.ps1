# Start Cloudflare Named Tunnel for local backend
# This script starts the named tunnel to expose the local FastAPI backend to the internet
# via a fixed domain: api.latextrans.online
# 
# Prerequisites:
#   1. cloudflared installed (winget install Cloudflare.cloudflared)
#   2. cloudflared tunnel login (one-time)
#   3. cloudflared tunnel create latextrans-api (one-time)
#   4. cloudflared tunnel route dns latextrans-api api.latextrans.online (one-time)
#   5. ~/.cloudflared/config.yml configured (one-time)
#
# Usage: .\scripts\start-tunnel.ps1

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  LaTeXTrans - Cloudflare Named Tunnel" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if cloudflared is installed
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    Write-Host "[ERROR] cloudflared is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install options:" -ForegroundColor Yellow
    Write-Host "  1. winget install Cloudflare.cloudflared"
    Write-Host "  2. Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    Write-Host ""
    exit 1
}

Write-Host "[INFO] Starting Named Tunnel 'latextrans-api'..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend will be accessible at:" -ForegroundColor Yellow
Write-Host "  https://api.latextrans.online" -ForegroundColor Cyan
Write-Host ""
Write-Host "Make sure the backend is running on localhost:8000" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

# Start the named tunnel
cloudflared tunnel run latextrans-api
