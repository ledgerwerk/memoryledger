# memoryledger skill

This skill guides agents to use the `memoryledger` CLI for reviewed long-term project memory and generated `AGENTS.md` files.

Use `memoryledger memory create` for candidates, `memoryledger review accept` for explicit approval, then `memoryledger render` and `memoryledger export` to update generated agent-facing files.

Do not edit configured or marker-owned generated targets directly. If export
finds a manual target, preserve it and preview `memoryledger agents adopt`;
replacement requires `--apply --backup`. Not every file in `docs/agents/` is
owned by memoryledger.
