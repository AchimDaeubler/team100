$ErrorActionPreference = 'Stop'

# Allocates the next sequential spec ID (zero-padded to 3 digits).
# Uses GitHub ref claims for atomicity; falls back to local-only scan when
# gh CLI is unavailable or the remote is unreachable.

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1
$specDir = Join-Path $repoRoot '.spec'

function Get-LocalMax {
    if (-not (Test-Path $specDir -PathType Container)) { return 0 }
    $max = 0
    foreach ($dir in Get-ChildItem -Path $specDir -Directory -Filter 'SPEC-*') {
        if ($dir.Name -match '^SPEC-(\d+)') {
            $num = [int]$Matches[1]
            if ($num -gt $max) { $max = $num }
        }
    }
    return $max
}

$localMax = Get-LocalMax

if (-not (Get-Command 'gh' -ErrorAction SilentlyContinue)) {
    Write-Host 'warning: gh CLI not found — using local-only ID; number may collide with concurrent users' -ForegroundColor Yellow
    Write-Output ('{0:D3}' -f ($localMax + 1))
    exit 0
}

# List existing remote claims
$remoteMax = 0
$refs = gh api "repos/{owner}/{repo}/git/matching-refs/spec-claims/SPEC-" --jq ".[].ref" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host 'warning: could not list remote ref claims — using local-only ID; number may collide with concurrent users' -ForegroundColor Yellow
    Write-Output ('{0:D3}' -f ($localMax + 1))
    exit 0
}
foreach ($line in @($refs)) {
    $text = "$line".Trim()
    if ($text -match 'SPEC-(\d+)') {
        $num = [int]$Matches[1]
        if ($num -gt $remoteMax) { $remoteMax = $num }
    }
}

# Cross-check remote branches for spec IDs not covered by ref claims
$branchMax = 0
$branches = gh api "repos/{owner}/{repo}/git/matching-refs/heads/SPEC-" --jq ".[].ref" 2>&1
if ($LASTEXITCODE -eq 0) {
    foreach ($line in @($branches)) {
        $text = "$line".Trim()
        if ($text -match 'SPEC-(\d+)') {
            $num = [int]$Matches[1]
            if ($num -gt $branchMax) { $branchMax = $num }
        }
    }
} else {
    Write-Host 'warning: could not list remote branches — branch collision check skipped' -ForegroundColor Yellow
}

# Cross-check open PR head branches for spec IDs
$prMax = 0
$prs = gh pr list --state open --json headRefName --jq ".[].headRefName" 2>&1
if ($LASTEXITCODE -eq 0) {
    foreach ($line in @($prs)) {
        $text = "$line".Trim()
        if ($text -match 'SPEC-(\d+)') {
            $num = [int]$Matches[1]
            if ($num -gt $prMax) { $prMax = $num }
        }
    }
} else {
    Write-Host 'warning: could not list open PRs — PR collision check skipped' -ForegroundColor Yellow
}

$candidate = [Math]::Max([Math]::Max($localMax, $remoteMax), [Math]::Max($branchMax, $prMax)) + 1
$sha = (git rev-parse HEAD) | Select-Object -First 1
$maxRetries = 10

for ($i = 0; $i -lt $maxRetries; $i++) {
    $padded = '{0:D3}' -f $candidate
    $refName = "refs/spec-claims/SPEC-$padded"

    $result = gh api "repos/{owner}/{repo}/git/refs" -f "ref=$refName" -f "sha=$sha" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output $padded
        exit 0
    }

    $resultText = ($result | Out-String)
    if ($resultText -match 'Reference already exists') {
        $candidate++
        continue
    }

    # Non-422 failure — fall back to local
    Write-Host 'warning: could not claim ref on remote — using local-only ID; number may collide with concurrent users' -ForegroundColor Yellow
    Write-Output ('{0:D3}' -f $candidate)
    exit 0
}

Write-Host 'warning: exhausted retry attempts — using local-only ID; number may collide with concurrent users' -ForegroundColor Yellow
Write-Output ('{0:D3}' -f $candidate)
exit 0
