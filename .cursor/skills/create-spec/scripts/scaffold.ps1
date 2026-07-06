param(
    [Parameter(Mandatory)][string]$Id,
    [Parameter(Mandatory)][string]$Slug,
    [Parameter(Mandatory)][string]$Category,
    [Parameter(Mandatory)][string]$Owner,
    [Parameter(ValueFromRemainingArguments)][string[]]$DependsOn
)

$ErrorActionPreference = 'Stop'

# Creates a spec directory with spec.md and meta.yaml from templates.
#
# Usage: scaffold.ps1 <id> <slug> <category> <owner> [depends_on...]

$repoRoot = (git rev-parse --show-toplevel) | Select-Object -First 1
$specDir = Join-Path $repoRoot '.spec'
$templatesDir = Join-Path (Join-Path (Join-Path (Join-Path (Join-Path $repoRoot '.cursor') 'skills') 'create-spec') 'assets') 'templates'

if (-not $Owner) {
    Write-Error "owner parameter is empty. Pass the output of 'git config user.name'."
    exit 1
}

$gitName = git config user.name 2>$null
if (-not $gitName) {
    Write-Warning "git config user.name is not configured. The owner value '$Owner' will be used as-is."
}

$validCategories = @('feature', 'bug', 'refactoring', 'testing')
if ($Category -notin $validCategories) {
    Write-Error "invalid category '$Category'. Must be one of: $($validCategories -join ', ')"
    exit 1
}

$templateFile = Join-Path $templatesDir "$Category-spec.md"
if (-not (Test-Path $templateFile)) {
    Write-Error "template not found at $templateFile"
    exit 1
}

$metaTemplate = Join-Path $templatesDir 'meta.yaml'
if (-not (Test-Path $metaTemplate)) {
    Write-Error "meta.yaml template not found at $metaTemplate"
    exit 1
}

$dirName = "SPEC-$Id-$Slug"
$specPath = Join-Path $specDir $dirName

if (Test-Path $specPath) {
    Write-Error "directory already exists: $specPath"
    exit 1
}

New-Item -ItemType Directory -Path $specPath -Force | Out-Null

$today = Get-Date -Format 'yyyy-MM-dd'

$specContent = (Get-Content $templateFile -Raw) `
    -replace '\{n\}', $Id `
    -replace '\{title\}', $Slug `
    -replace '\{owner\}', $Owner `
    -replace 'category: feature', "category: $Category"
Set-Content -Path (Join-Path $specPath 'spec.md') -Value $specContent -NoNewline

$metaContent = (Get-Content $metaTemplate -Raw) -replace '\{date\}', $today
Set-Content -Path (Join-Path $specPath 'meta.yaml') -Value $metaContent -NoNewline

if ($DependsOn -and $DependsOn.Count -gt 0) {
    $depsBlock = "`ndepends_on:`n"
    foreach ($dep in $DependsOn) {
        $depsBlock += "  - `"$dep`"`n"
    }
    Add-Content -Path (Join-Path $specPath 'meta.yaml') -Value $depsBlock -NoNewline
}

Write-Output $specPath
