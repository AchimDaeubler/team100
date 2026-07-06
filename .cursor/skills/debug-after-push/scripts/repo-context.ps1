# Gathers repo context for debug-after-push: remote URL, current branch,
# HEAD SHA, service name, and deploy branch from the build workflow.

$ErrorActionPreference = "Stop"

Write-Output "=== Repo Context ==="

$RemoteUrl = git remote get-url origin 2>$null
if (-not $RemoteUrl) { $RemoteUrl = "unknown" }

$Branch = git branch --show-current 2>$null
if (-not $Branch) { $Branch = "detached" }

$HeadSha = git rev-parse HEAD 2>$null
if (-not $HeadSha) { $HeadSha = "unknown" }

Write-Output "remote_url: $RemoteUrl"
Write-Output "branch: $Branch"
Write-Output "head_sha: $HeadSha"

$Workflow = ".github/workflows/build.yml"

if (Test-Path $Workflow) {
    $Content = Get-Content $Workflow -Raw

    $ServiceMatch = [regex]::Match($Content, '^\s+(\w+):Dockerfile', 'Multiline')
    if ($ServiceMatch.Success) {
        $ServiceName = $ServiceMatch.Groups[1].Value
        Write-Output "service_name: $ServiceName"
    } else {
        $RepoRoot = git rev-parse --show-toplevel 2>$null
        $ServiceName = Split-Path $RepoRoot -Leaf
        Write-Output "service_name: $ServiceName (fallback: repo name)"
    }

    $DeployMatch = [regex]::Match($Content, "refs/heads/([^'""]+)")
    if ($DeployMatch.Success) {
        Write-Output "deploy_branch: $($DeployMatch.Groups[1].Value)"
    } else {
        Write-Output "deploy_branch: unknown"
    }
} else {
    $RepoRoot = git rev-parse --show-toplevel 2>$null
    $ServiceName = Split-Path $RepoRoot -Leaf
    Write-Output "service_name: $ServiceName (fallback: no workflow found)"
    Write-Output "deploy_branch: unknown (no workflow found)"
}
