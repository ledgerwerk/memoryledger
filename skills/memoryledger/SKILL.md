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
2. Create or update memory with `memoryledger memory create`, `memoryledger memory update`, or `memoryledger memory append`.
3. Use `memoryledger review accept` only when the user clearly approved the memory or an explicit template policy allows acceptance.
4. For the common approved workflow, run `memoryledger finalize --accept-all --reason "..." --export`. Otherwise run `memoryledger build` then `memoryledger export`.
5. Use `--include-nested` only when nested export is enabled or explicitly requested.
6. Show the resulting `AGENTS.md` path and any linked document paths.
7. Keep root `AGENTS.md` concise and move long memory to linked documents.

## Forbidden workflow

Do not:

- write `AGENTS.md` directly
- patch `AGENTS.md` directly
- write nested `AGENTS.md` directly
- treat `AGENTS.md` as the canonical memory store
- accept candidate memory without explicit approval, review reason, or explicit template policy

Never edit a configured generated target, or any file containing the
memoryledger generated marker, directly. `AGENTS.md` and configured linked
document paths are not automatically generated merely because of their names;
ownership is established by configuration and the generated marker.

For multiline memories or text containing shell syntax, use `--stdin` with a
single-quoted heredoc. Do not pass long memory bodies through `--text`:

```bash
cat <<'EOF' | memoryledger memory create \
  --kind learning \
  --title "Package workflow lesson" \
  --scope repo \
  --stdin \
  --evidence "User approved run learning."
Use literal shell syntax like ${stdenv.hostPlatform.system} safely here.
EOF
```

Use built-in kinds: rule, learning, episode, procedure, semantic, document, local.
The CLI silently normalizes supported aliases such as `package-workflow` to
`procedure` and `project` scope to `repo`. Run `memoryledger schema values` to
list valid canonical values.

Examples:

- User: `build an AGENTS.md`
  - Agent must: create memories, accept approved memories, render, export.
  - Agent must not: write `AGENTS.md` directly.
- User: `add this to AGENTS.md`
  - Agent must: create or update a memory record for the instruction, then render/export if approved.
  - Agent must not: patch `AGENTS.md`.

## Migrating an existing AGENTS.md

If export reports `manual_file`, preserve the file. Do not overwrite it.

1. Run `memoryledger agents adopt AGENTS.md --json` for a read-only migration plan.
2. Inspect the source hash, headings, proposed memories, target placement, and whether the root is expected to shrink.
3. If the user approves, run `memoryledger agents adopt AGENTS.md --apply --backup --accept --reason "..."`.
4. Run `memoryledger agents verify-adoption --source AGENTS.md.memoryledger-adopt-1.bak`.
5. Run `memoryledger finalize --accept-all --reason "..." --export`, or run `memoryledger build` and `memoryledger export` separately.
6. Report whether the generated root became shorter and where the full migrated content lives.

Adoption preserves the full original source as a generated linked document. The
root `AGENTS.md` should clearly state that linked documents are generated memory
and part of the agent context.

## Storage and linked-doc migrations

Canonical durable Memoryledger state is owned by Ledgercore schema 3:

- shared manifest: `.ledger/ledger.toml`
- project tool config: `.ledger/memoryledger/config.toml`
- durable data: `.ledger/memoryledger/data/`
- rendered previews: the resolved `artifacts` cache mount

Use `memoryledger storage where` and `memoryledger storage validate --strict` for
read-only diagnostics. Do not manually copy `.memoryledger` into `.ledger`.
Migrate an existing legacy project explicitly with
`memoryledger migrate plan storage-layout`, then
`memoryledger migrate apply storage-layout`; use `migrate recover` for an interrupted
migration and `migrate cleanup storage-layout --dry-run` before any removal. Migration
is copy-first, hash-verified, manifest-last, and retains the legacy source until
verified cleanup.

Storage v2 uses one front-matter Markdown file per memory under `.memoryledger/memories/`.
Use `memoryledger migrate plan storage-v2` before `migrate apply storage-v2 --backup` when converting legacy sidecar records.
Generated linked documents default to `agent_docs/`. Use `memoryledger migrate plan linked-docs-dir` before `migrate apply`; it moves only files containing the generated marker.

## Implementation workflow memory

When implementation work is requested, load the planledger skill first and create a plan.
Export the rendered plan file and present it to the user.
When implementation starts, load taskledger and create a new task.
