param(
    [Parameter(Mandatory)][string]$OldId,
    [Parameter(Mandatory)][string]$NewId
)

$ErrorActionPreference = 'Stop'

# Renumbers a spec after a collision is detected. Renames
# .spec/SPEC-{old}-{slug}/ to .spec/SPEC-{new}-{slug}/ via `git mv` and
# updates the `id:` frontmatter line in spec.md so the directory path and
# the frontmatter agree.
#
# Usage: renumber.ps1 <old-id> <new-id>
#   old-id - existing spec number (1-3 digits; "023" and "23" both accepted)
#   new-id - desired spec number (1-3 digits; "026" and "26" both accepted)
#
# Preflight refusals (non-zero exit, actionable error on stderr):
#   - args missing or not 1-3 digits
#   - old and new IDs are the same
#   - working tree is not clean (git status --porcelain non-empty)
#   - no directory .spec/SPEC-{old}-*/ exists, or more than one matches
#   - the old directory has no spec.md
#   - a directory .spec/SPEC-{new}-*/ already exists
#
# Does not renumber cross-spec references in other specs' meta.yaml or
# prose, rename branches, edit PR titles, or rewrite commit messages.
# See .cursor/skills/create-spec/references/renumbering.md for the
# manual follow-up checklist.

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1
$specDir = Join-Path $repoRoot '.spec'

if ($OldId -notmatch '^\d{1,3}$') {
    Write-Error "old-id '$OldId' must be 1-3 digits"
    exit 1
}
if ($NewId -notmatch '^\d{1,3}$') {
    Write-Error "new-id '$NewId' must be 1-3 digits"
    exit 1
}

$oldPadded = '{0:D3}' -f [int]$OldId
$newPadded = '{0:D3}' -f [int]$NewId

if ($oldPadded -eq $newPadded) {
    Write-Error "old-id and new-id are the same (SPEC-$oldPadded)"
    exit 1
}

$porcelain = git status --porcelain
if ($porcelain) {
    Write-Error "working tree is dirty. Commit or stash changes before renumbering."
    exit 1
}

$oldCandidates = @(Get-ChildItem -Path $specDir -Directory -Filter "SPEC-$oldPadded-*" -ErrorAction SilentlyContinue)
if ($oldCandidates.Count -eq 0) {
    Write-Error "no directory found matching .spec/SPEC-$oldPadded-*/"
    exit 1
}
if ($oldCandidates.Count -gt 1) {
    Write-Error "multiple directories match .spec/SPEC-$oldPadded-*/ - resolve manually"
    exit 1
}

$oldDir = $oldCandidates[0].FullName
$oldBase = $oldCandidates[0].Name
$slug = $oldBase.Substring("SPEC-$oldPadded-".Length)
$newBase = "SPEC-$newPadded-$slug"
$newDir = Join-Path $specDir $newBase

$oldSpec = Join-Path $oldDir 'spec.md'
if (-not (Test-Path $oldSpec)) {
    Write-Error "spec.md not found at $oldSpec"
    exit 1
}

$newExisting = @(Get-ChildItem -Path $specDir -Directory -Filter "SPEC-$newPadded-*" -ErrorAction SilentlyContinue)
if ($newExisting.Count -gt 0) {
    Write-Error ".spec/SPEC-$newPadded-* already exists - new ID is claimed locally"
    exit 1
}

$mvOutput = git mv $oldDir $newDir 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "git mv '$oldBase' -> '$newBase' failed: $mvOutput"
    exit 1
}

$newSpec = Join-Path $newDir 'spec.md'
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$content = [System.IO.File]::ReadAllText($newSpec, $utf8NoBom)
$regex = [regex]::new('(?m)^id: SPEC-\d{3}$')
$newContent = $regex.Replace($content, "id: SPEC-$newPadded", 1)
[System.IO.File]::WriteAllText($newSpec, $newContent, $utf8NoBom)

Write-Output "Renumbered $oldBase -> $newBase"
