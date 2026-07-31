# Evidence

Evidence references use the kinds `file`, `config`, `run`, `command`,
`user_approval`, and `external`. Every reference has a title and URI and may
include line ranges, an excerpt, a content hash, and a timestamp.

File and config evidence must remain confined to the workspace. Internal run
evidence uses an opaque run URI rather than copying an entire transcript. The
guardrails reject secret-like values and unsafe paths; excerpts should be the
smallest useful proof. Evidence comments can explain why a reference supports
the memory, and `include_evidence` can enable an evidence index in rendered
output.

Add evidence with:

```bash
memoryledger memory evidence add memory-0001 \
  --kind file --title "Policy source" --uri README.md \
  --reason "The repository states this rule."
```
