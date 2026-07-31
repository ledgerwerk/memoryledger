# memoryledger skill

This skill guides agents to use the `memoryledger` CLI for reviewed long-term project memory and generated `AGENTS.md` files.

`AGENTS.md` is generated. Durable project memory lives in `.memoryledger/`. Storage v2 stores each memory as `.memoryledger/memories/memory-NNNN.md` with YAML front matter.

Use `memoryledger memory create` for candidates, `memoryledger review accept` for explicit approval, then `memoryledger finalize --accept-all --reason "..." --export` when the user approved the candidates. Otherwise run `memoryledger build` and `memoryledger export` separately.

If the user says `build an AGENTS.md` or `add this to AGENTS.md`, create or update memory records first. Do not write `AGENTS.md` directly.

Do not edit configured or marker-owned generated targets directly. If export finds a manual target, preserve it and preview `memoryledger agents adopt`; replacement requires `--apply --backup`. Not every file in `agent_docs/` is owned by memoryledger.

For legacy projects, use `memoryledger migrate plan storage-v2` before `migrate apply storage-v2`. Use `memoryledger migrate plan linked-docs-dir` before `migrate apply linked-docs-dir`; it moves only generated files with the marker.

For multiline or shell-sensitive content, prefer `--stdin` with a single-quoted heredoc. The CLI silently normalizes supported aliases such as kind `package-workflow` to `procedure` and scope `project` to `repo`.
