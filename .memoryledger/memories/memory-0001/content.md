`memoryledger` is a Python CLI and library for auditable long-term project memory and deterministic `AGENTS.md` rendering. Its core contract is: capture memory as durable candidate records, require explicit review before acceptance, render only reviewed memory by default, and export generated agent files safely.

Canonical workflow:

```text
init -> memory create -> review accept -> render -> export
```

This workflow is the product contract, not decoration.
