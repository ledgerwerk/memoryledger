# memoryledger skill

This skill guides agents to use the `memoryledger` CLI for reviewed long-term project memory and generated `AGENTS.md` files.

`AGENTS.md` is generated. Durable project memory lives in `.memoryledger/`.

Use `memoryledger memory create` for candidates, `memoryledger review accept`
for explicit approval, then `memoryledger render` and `memoryledger export` to
update generated agent-facing files.

If the user says `build an AGENTS.md` or `add this to AGENTS.md`, create or
update memory records first. Do not write `AGENTS.md` directly.

Do not edit configured or marker-owned generated targets directly. If export
finds a manual target, preserve it and preview `memoryledger agents adopt`;
replacement requires `--apply --backup`. Not every file in `agent_docs/` is
owned by memoryledger.
