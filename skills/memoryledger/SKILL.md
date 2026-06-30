---
name: memoryledger
description: Use memoryledger when the user asks to remember project instructions, store project memory, update AGENTS.md, review runs for durable memory, create nested AGENTS.md files, or move long memory to linked agent documents.
license: Apache-2.0
---

## When to use

Use this skill when the user says things like:

- `memoryledger: always use planledger first`
- remember this for this project
- store this as project memory
- add this to AGENTS.md
- review this run for durable memory
- parse run.html for important memory
- create nested AGENTS.md for this package
- move long memory to a linked agent document

## Workflow

1. Treat user-provided memory as a candidate unless the user explicitly approves it.
2. Prefer `memoryledger memory create`; creation stores candidates by default.
3. Use `memoryledger review accept` only when the user clearly approved the memory.
4. Run `memoryledger render`.
5. Run `memoryledger export`.
6. Use `--include-nested` only when nested export is enabled or explicitly requested.
7. Show the resulting `AGENTS.md` path and any linked document paths.
8. Keep root `AGENTS.md` concise.

Never edit a configured generated target, or any file containing the
memoryledger generated marker, directly. `AGENTS.md` and files under
`docs/agents/` are not automatically generated merely because of their names;
ownership is established by configuration and the generated marker.

If export reports `MANUAL_FILE`, preserve the file. Preview it with
`memoryledger agents adopt`, then use the dedicated
`memoryledger agents adopt --apply --backup` transaction only after reviewing
the proposals. Add `--accept --reason "..."` only with explicit approval.

## Implementation workflow memory

When implementation work is requested, load the planledger skill first and create a plan.
Export the rendered plan file and present it to the user.
When implementation starts, load taskledger and create a new task.
