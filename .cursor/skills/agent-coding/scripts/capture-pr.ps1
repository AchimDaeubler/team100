param(
    [Parameter(Mandatory)][string]$SpecDir,
    [Parameter(Mandatory)][string]$PrUrl
)

$ErrorActionPreference = 'Stop'

# Appends a PR URL to meta.yaml's completion.pull_requests list.
# Invoked by spec-retro (auto-chained or standalone). Idempotent:
# re-invoking with a URL already present in pull_requests is a no-op.
# The completion block with pull_requests: [] must already exist.
#
# Usage: capture-pr.ps1 <spec-directory> <pr-url>

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1

if (-not [System.IO.Path]::IsPathRooted($SpecDir)) {
    $SpecDir = Join-Path $repoRoot $SpecDir
}

$metaFile = Join-Path $SpecDir 'meta.yaml'

if (-not (Test-Path $metaFile)) {
    Write-Error "meta.yaml not found at $metaFile"
    exit 1
}

$content = Get-Content $metaFile
$hasCompletion = $content | Where-Object { $_ -match '^completion:' }
if (-not $hasCompletion) {
    Write-Error "no completion block found in $metaFile. Run transition.ps1 to done first."
    exit 1
}

# Idempotency pre-check: walk real (non-commented) list entries under the
# pull_requests: key and exact-match against $PrUrl. The template keeps
# a commented `# pull_requests:` example that must not be treated as real.
$prFound = $false
$inPullRequests = $false
foreach ($line in $content) {
    if ($line.TrimStart() -match '^\#') {
        continue
    }
    if ($line -match 'pull_requests:') {
        if ($line -match '\[\]') {
            $inPullRequests = $false
        } else {
            $inPullRequests = $true
        }
        continue
    }
    if ($inPullRequests) {
        if ($line.Trim() -match '^- ') {
            $entry = $line.Trim()
            $entry = $entry -replace '^- ', ''
            $entry = $entry -replace '^"', ''
            $entry = $entry -replace '"$', ''
            if ($entry -eq $PrUrl) {
                $prFound = $true
                break
            }
        } else {
            $inPullRequests = $false
        }
    }
}

if ($prFound) {
    $dirName = Split-Path $SpecDir -Leaf
    Write-Output "PR URL already recorded in $dirName/meta.yaml"
    exit 0
}

$output = @()
$i = 0
while ($i -lt $content.Count) {
    $line = $content[$i]

    # Skip YAML comment lines — the template block contains a commented
    # pull_requests: that must not be treated as a real field.
    $isComment = $line.TrimStart() -match '^\#'

    # Match 'pull_requests: []' and replace with list entry
    if (-not $isComment -and $line -match 'pull_requests:\s*\[\]') {
        $indent = ''
        if ($line -match '^(\s+)') { $indent = $Matches[1] }
        $output += "${indent}pull_requests:"
        $output += "${indent}  - `"$PrUrl`""
        $i++
        continue
    }

    # Match 'pull_requests:' with existing entries — append after last entry
    if (-not $isComment -and $line -match 'pull_requests:' -and $line -notmatch '\[\]') {
        $output += $line
        $i++
        while ($i -lt $content.Count -and $content[$i].Trim() -match '^- ') {
            $output += $content[$i]
            $i++
        }
        $indent = ''
        if ($line -match '^(\s+)') { $indent = $Matches[1] }
        $output += "${indent}  - `"$PrUrl`""
        continue
    }

    $output += $line
    $i++
}

Set-Content -Path $metaFile -Value $output

$dirName = Split-Path $SpecDir -Leaf
Write-Output "Added $PrUrl to $dirName/meta.yaml"
