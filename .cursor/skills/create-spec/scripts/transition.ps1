param(
    [Parameter(Mandatory)][string]$SpecDir,
    [Parameter(Mandatory)][string]$TargetStatus
)

$ErrorActionPreference = 'Stop'

# Updates status and updated fields in a spec's meta.yaml.
#
# Usage: transition.ps1 <spec-directory> <target-status>

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1

if (-not [System.IO.Path]::IsPathRooted($SpecDir)) {
    $SpecDir = Join-Path $repoRoot $SpecDir
}

$metaFile = Join-Path $SpecDir 'meta.yaml'

if (-not (Test-Path $metaFile)) {
    Write-Error "meta.yaml not found at $metaFile"
    exit 1
}

$validStatuses = @('draft', 'research', 'ready', 'in_progress', 'blocked', 'done', 'cancelled', 'superseded')
if ($TargetStatus -notin $validStatuses) {
    Write-Error "invalid status '$TargetStatus'. Must be one of: $($validStatuses -join ', ')"
    exit 1
}

$today = Get-Date -Format 'yyyy-MM-dd'
$content = Get-Content $metaFile

$content = $content -replace '^status:.*', "status: $TargetStatus"
$content = $content -replace '^updated:.*', "updated: $today"

if ($TargetStatus -eq 'ready') {
    $currentSha = (git rev-parse HEAD) | Select-Object -First 1
    $hasSha = $content | Where-Object { $_ -match '^ready_sha:' }
    if ($hasSha) {
        $content = $content -replace '^ready_sha:.*', "ready_sha: `"$currentSha`""
    } else {
        $content += "ready_sha: `"$currentSha`""
    }
}

if ($TargetStatus -eq 'done') {
    $hasCompletion = $content | Where-Object { $_ -match '^completion:' }
    if (-not $hasCompletion) {
        $content += ''
        $content += 'completion:'
        $content += "  date: $today"
        $content += '  pull_requests: []'
    }
}

Set-Content -Path $metaFile -Value $content

$dirName = Split-Path $SpecDir -Leaf
Write-Output "Transitioned $dirName to $TargetStatus"
