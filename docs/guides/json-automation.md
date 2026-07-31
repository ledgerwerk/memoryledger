# JSON automation

Machine integrations should use the `ledgerwerk.cli.v1` envelope and process
the exit code, not parse human output.

```json
{
  "schema": "ledgerwerk.cli.v1",
  "ok": true,
  "tool": "memoryledger",
  "command": "status",
  "result": {},
  "events": [],
  "warnings": []
}
```

Errors use the same envelope:

```json
{
  "schema": "ledgerwerk.cli.v1",
  "ok": false,
  "tool": "memoryledger",
  "command": "memory show",
  "error": {
    "code": "not-found",
    "message": "Memory not found.",
    "details": { "domain_code": "NOT_FOUND" },
    "remediation": []
  },
  "events": [],
  "warnings": []
}
```

Global options are `--root PATH`, `--json`, and `--version`. Exit codes are:

| Code | Meaning                         |
| ---: | ------------------------------- |
|    0 | Success                         |
|    1 | Domain failure                  |
|    2 | Usage or invalid input          |
|    3 | Unavailable or missing resource |
|    4 | Conflict or failed precondition |
|    5 | External process failure        |
