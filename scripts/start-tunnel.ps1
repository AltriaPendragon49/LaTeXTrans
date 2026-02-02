# Start Cloudflare Tunnel for local backend
# This script starts a temporary tunnel to expose the local FastAPI backend to the internet
# 
# Usage: .\scripts\start-tunnel.ps1
# The script will output a public URL (e.g., https://xxx-xxx.trycloudflare.com)
# Use this URL as your VITE_API_URL when deploying the frontend

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  LaTeXTrans - Cloudflare Tunnel Starter" -ForegroundColor Cyan
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

Write-Host "[INFO] Starting Cloudflare Tunnel for localhost:8000..." -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "  1. Copy the public URL from the output below"
Write-Host "  2. Use it as VITE_API_URL when deploying frontend"
Write-Host "  3. Keep this terminal open while testing"
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan

# Start the tunnel
cloudflared tunnel --url http://localhost:8000
