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
- build an AGENTS.md
- update AGENTS.md
- review this run for durable memory
- parse run.html for important memory
- create nested AGENTS.md for this package
- move long memory to a linked agent document

## Non-negotiable rule

When this skill is active, `AGENTS.md` updates must go through memoryledger records.

Treat `AGENTS.md`, nested `AGENTS.md`, and any configured or marker-owned linked
agent docs as generated artifacts.

Never create or edit `AGENTS.md` directly. Never patch a generated linked agent
document directly.

Use memory records as the source of truth, then render and export.

## Required workflow

1. Treat user-provided memory as a candidate unless the user explicitly approves it.
2. Create or update memory with `memoryledger memory create`, `memoryledger memory edit`, or `memoryledger memory append`.
3. Use `memoryledger review accept` only when the user clearly approved the memory or an explicit template policy allows acceptance.
4. Run `memoryledger render`.
5. Run `memoryledger export`.
6. Use `--include-nested` only when nested export is enabled or explicitly requested.
7. Show the resulting `AGENTS.md` path and any linked document paths.
8. Keep root `AGENTS.md` concise and move long memory to linked documents.

## Forbidden workflow

Do not:

- write `AGENTS.md` directly
- patch `AGENTS.md` directly
- write nested `AGENTS.md` directly
- treat `AGENTS.md` as the canonical memory store
- accept candidate memory without explicit approval, review reason, or explicit template policy

Never edit a configured generated target, or any file containing the
memoryledger generated marker, directly. `AGENTS.md` and files under
`docs/agents/` are not automatically generated merely because of their names;
ownership is established by configuration and the generated marker.

Examples:

- User: `build an AGENTS.md`
  - Agent must: create memories, accept approved memories, render, export.
  - Agent must not: write `AGENTS.md` directly.
- User: `add this to AGENTS.md`
  - Agent must: create or update a memory record for the instruction, then render/export if approved.
  - Agent must not: patch `AGENTS.md`.

If export reports `MANUAL_FILE`, preserve the file. Preview it with
`memoryledger agents adopt`, then use the dedicated
`memoryledger agents adopt --apply --backup` transaction only after reviewing
the proposals. Add `--accept --reason "..."` only with explicit approval.

## Implementation workflow memory

When implementation work is requested, load the planledger skill first and create a plan.
Export the rendered plan file and present it to the user.
When implementation starts, load taskledger and create a new task.
