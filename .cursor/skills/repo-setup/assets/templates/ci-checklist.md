# CI Readiness Checklist

Quality gates that a Creator-ready repo's CI pipeline should cover. Walk
through each item with the team and note any gaps as follow-up items.

If the development environment was scaffolded in a previous step, reference
the specific tools that are installed rather than the generic examples below.

## Required gates

### 1. Type checking

- [ ] Static type checking runs on every PR
- Tool: [e.g., `tsc --noEmit`, `mypy`, `go vet`, Java compiler]
- Blocks merge on failure: yes / no

### 2. Linting

- [ ] Linter runs on every PR
- Tool: [e.g., ESLint, Ruff/Flake8, golangci-lint, Checkstyle]
- Config committed to repo: yes / no
- Blocks merge on failure: yes / no

### 3. Test runner

- [ ] Tests run on every PR
- Tool: [e.g., Jest, pytest, `go test`, JUnit]
- Types covered: unit / integration / e2e
- Blocks merge on failure: yes / no

### 4. Security scanning

- [ ] Dependency vulnerability scanning enabled
- Tool: [e.g., Dependabot, Snyk, Trivy, npm audit]
- [ ] Static analysis / SAST enabled (optional but recommended)
- Tool: [e.g., CodeQL, Semgrep, SonarQube]
- Blocks merge on failure: yes / no

### 5. Coverage thresholds

- [ ] Code coverage measured and reported
- Tool: [e.g., Istanbul/nyc, coverage.py, JaCoCo]
- Threshold: [e.g., 80% line coverage, or "no threshold yet"]
- Blocks merge on failure: yes / no

## Recommended additions

### 6. Build verification

- [ ] Project builds successfully on every PR
- Catches: missing imports, compilation errors, asset pipeline failures

### 7. Formatting check

- [ ] Formatter runs in check mode on every PR
- Tool: [e.g., Prettier --check, Black --check, gofmt -l]
- Prevents style debates in review

### 8. Commit message validation

- [ ] Commit messages validated against format (optional)
- Tool: [e.g., commitlint, conventional-commits]

## Follow-up items

List any gaps identified during the review:

1. [Gap description — what's missing and recommended action]
2. ...
