# Common Failure Patterns

| Symptom | Likely cause | Where to look |
|---------|-------------|--------------|
| Build fails at Docker step | Missing dependency, syntax error | `gh run view --log-failed` |
| Build passes, deploy fails | Misconfigured secrets, GitOps permissions | Deploy job logs |
| CI green, app crashes on startup | Missing env var, DB connection failure | Datadog `status:error` near deploy time |
| CI green, HTTP errors at runtime | Application bug, route misconfiguration | Datadog `status:error` filtered by endpoint |
