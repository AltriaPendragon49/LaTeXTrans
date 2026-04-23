$ErrorActionPreference = "Stop"

$DeployScript = Join-Path $PSScriptRoot "deploy-frontend.ps1"
$WranglerConfig = Join-Path $PSScriptRoot "..\frontend\wrangler.toml"

if (-not (Test-Path $DeployScript)) {
    throw "Deploy script not found: $DeployScript"
}

if (-not (Test-Path $WranglerConfig)) {
    throw "Wrangler config not found: $WranglerConfig"
}

$deployContent = Get-Content -Raw $DeployScript
$wranglerContent = Get-Content -Raw $WranglerConfig

$requiredDeployPatterns = @(
    @{
        Name = "checked external command helper"
        Pattern = "function Invoke-CheckedCommand"
    },
    @{
        Name = "branch deployment parameter"
        Pattern = '\[string\]\$Branch'
    },
    @{
        Name = "preview deployment confirmation switch"
        Pattern = 'AllowPreview'
    },
    @{
        Name = "default branch detection"
        Pattern = 'git"\s+-ArgumentList\s+@\("symbolic-ref",\s+"refs/remotes/origin/HEAD"\)'
    },
    @{
        Name = "command failure exit-code guard"
        Pattern = '\$LASTEXITCODE\s*-ne\s*0'
    },
    @{
        Name = "wrangler preflight check"
        Pattern = 'Invoke-CheckedCommand[\s\S]*"wrangler"[\s\S]*"whoami"'
    },
    @{
        Name = "optional preflight skip switch"
        Pattern = 'SkipPreflight'
    },
    @{
        Name = "preview deployment safeguard message"
        Pattern = 'preview deployment'
    },
    @{
        Name = "branch-aware wrangler deploy"
        Pattern = '--project-name",\s+\$ProjectName,\s+"--branch",\s+\$Branch'
    }
)

foreach ($check in $requiredDeployPatterns) {
    if ($deployContent -notmatch $check.Pattern) {
        throw "Missing deploy script safeguard: $($check.Name)"
    }
}

if ($wranglerContent -notmatch 'pages_build_output_dir\s*=\s*"\.?/?dist"') {
    throw 'Missing required Cloudflare Pages key: pages_build_output_dir = "./dist"'
}

Write-Host "[PASS] Frontend deploy safeguards are present." -ForegroundColor Green
