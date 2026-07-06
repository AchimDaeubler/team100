# Runtime Logs (Datadog)

Skip if no deploy has run (nothing deployed to check).

Use whichever Datadog MCP server is available. If none responds, `[NOTE]`
tell the user:

> "Datadog MCP is not available. This usually means the Datadog plugin or
> Datadog MCP server is not available nor not authenticated. Make sure the
> Datadog MCP server is configured in Cursor as plugin, extension or MCP.
> Also ensure the Datadog is assigned to your account on `trimble.okta.com`.
> In the meantime, try checking Datadog logs manually by searching for
> `service:<service-name>` in Datadog."

## Search for errors

```
query:   "service:<service-name> status:error"
from:    "now-1h"    (widen if the deploy was older)
```

If errors are found, fetch surrounding logs for context (startup sequence,
preceding events):

```
query:   "service:<service-name>"
from:    <slightly before first error>
to:      <slightly after last error>
```

## Aggregate patterns (if many errors)

Use `analyze_datadog_logs` when there are too many individual errors to
read through:

```
filter:      "service:<service-name> status:error"
sql_query:   "SELECT message, count(*) FROM logs GROUP BY message ORDER BY count(*) DESC"
from:        "now-1h"
```
