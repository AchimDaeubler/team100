param(
    [Parameter(Mandatory)][string]$SpecDir,
    [Parameter()][string]$Flag
)

$ErrorActionPreference = 'Stop'

# Compares ready_sha against HEAD for files listed in the spec's
# "Files likely affected" section. Prints changed files, if any.
#
# Usage: freshness-diff.ps1 <spec-directory> [--name-status]

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1
$diffFlag = '--name-only'
if ($Flag -eq '--name-status') { $diffFlag = '--name-status' }

if (-not [System.IO.Path]::IsPathRooted($SpecDir)) {
    $SpecDir = Join-Path $repoRoot $SpecDir
}

$metaFile = Join-Path $SpecDir 'meta.yaml'
$specFile = Join-Path $SpecDir 'spec.md'

if (-not (Test-Path $metaFile)) {
    Write-Error "meta.yaml not found at $metaFile"
    exit 1
}

if (-not (Test-Path $specFile)) {
    Write-Error "spec.md not found at $specFile"
    exit 1
}

$readySha = $null
foreach ($line in Get-Content $metaFile) {
    if ($line -match '^ready_sha:\s*"?([^"]+)"?') {
        $readySha = $Matches[1].Trim()
        break
    }
}

if (-not $readySha) {
    Write-Host 'info: no ready_sha in meta.yaml, skipping freshness check' -ForegroundColor Yellow
    exit 0
}

$verifyResult = git rev-parse --verify "$readySha^{commit}" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "warning: ready_sha $readySha is not a valid commit in this repo" -ForegroundColor Yellow
    Write-Host 'recommendation: full re-research' -ForegroundColor Yellow
    exit 0
}

function Extract-Paths {
    $inSection = $false
    $paths = @()
    foreach ($line in Get-Content $specFile) {
        if ($line -match '(?i)Files likely affected') {
            $inSection = $true
            continue
        }
        if ($inSection) {
            if ($line -match '(?i)(Files NOT to modify|^##|Patterns to follow|Test expectations)') {
                break
            }
            if ($line -match '`([^`]+)`') {
                $paths += $Matches[1]
            } elseif ($line -match '^\s*[-*]\s+(\S+\.\S+)') {
                $paths += $Matches[1]
            }
        }
    }
    return $paths
}

$paths = Extract-Paths

if ($paths.Count -eq 0) {
    Write-Host 'info: no file paths extracted from spec.md, skipping path-limited diff' -ForegroundColor Yellow
    exit 0
}

git diff $diffFlag $readySha HEAD -- @paths
