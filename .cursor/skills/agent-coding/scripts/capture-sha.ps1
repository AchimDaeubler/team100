param(
    [Parameter(Mandatory)][string]$SpecDir
)

$ErrorActionPreference = 'Stop'

# Records ready_sha in a spec's meta.yaml from current git rev-parse HEAD.
#
# Usage: capture-sha.ps1 <spec-directory>

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1

if (-not [System.IO.Path]::IsPathRooted($SpecDir)) {
    $SpecDir = Join-Path $repoRoot $SpecDir
}

$metaFile = Join-Path $SpecDir 'meta.yaml'

if (-not (Test-Path $metaFile)) {
    Write-Error "meta.yaml not found at $metaFile"
    exit 1
}

$currentSha = (git rev-parse HEAD) | Select-Object -First 1
$content = Get-Content $metaFile

$hasSha = $content | Where-Object { $_ -match '^ready_sha:' }
if ($hasSha) {
    $content = $content -replace '^ready_sha:.*', "ready_sha: `"$currentSha`""
} else {
    $content += "ready_sha: `"$currentSha`""
}

Set-Content -Path $metaFile -Value $content

Write-Output $currentSha
