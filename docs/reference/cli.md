<!-- Generated from memoryledger.command_catalog and the Typer command tree. -->
<!-- Do not edit directly. -->

# CLI reference

The canonical command reference is generated from the Typer command tree and `memoryledger.command_catalog.CATALOG`.

```{note}
Deprecated compatibility aliases are listed in [Deprecations](deprecations).
```

## Agents

### `agents adopt`

Adopt an existing AGENTS.md into memory records.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger agents adopt`

**Arguments and options**

- `target` — argument; optional; type `path`; default `AGENTS.md`
- `--apply` — option; optional; type `boolean`; flag
- `--backup` — option; optional; type `boolean`; flag
- `--accept` — option; optional; type `boolean`; flag
- `--reason` — option; optional; type `text`; default ``
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger agents adopt
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `agents plan`

Print the canonical agent workflow commands.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger agents plan`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger agents plan
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `agents verify-adoption`

Verify that adopted memories match a source AGENTS.md.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger agents verify-adoption`

**Arguments and options**

- `--source` — option; required; type `path`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger agents verify-adoption
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Configuration

### `config show`

Show effective configuration with source tracking.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger config show`

**Arguments and options**

- None.

**Example**

```bash
memoryledger config show
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `config validate`

Validate configuration without writing.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger config validate`

**Arguments and options**

- None.

**Example**

```bash
memoryledger config validate
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Evidence

### `evidence scan`

Scan repository evidence and propose candidate memories.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger evidence scan`

**Arguments and options**

- `--apply-candidates` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger evidence scan
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Import

### `import current-run`

Import memory candidates from the current agent run.

- **Audience:** `agent`
- **Stability:** `beta`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger import current-run`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger import current-run
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `import run-html`

Import memory candidates from run HTML logs.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger import run-html`

**Arguments and options**

- `--file` — option; required; type `path`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger import run-html
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `import text`

Import memory candidates from text input.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger import text`

**Arguments and options**

- `--text` — option; optional; type `text`
- `--file` — option; optional; type `path`
- `--stdin` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger import text
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Memory

### `memory append`

Append text to the body of a memory record.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory append`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--reason` — option; required; type `text`
- `--text` — option; optional; type `text`
- `--file` — option; optional; type `path`
- `--stdin` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory append
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory archive`

Archive a memory record (convenience wrapper for set-status archived).

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory archive`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--reason` — option; required; type `text`

**Example**

```bash
memoryledger memory archive
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory create`

Create a new memory record.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger memory create`

**Arguments and options**

- `--kind` — option; required; type `text`
- `--title` — option; required; type `text`
- `--text` — option; optional; type `text`
- `--file` — option; optional; type `path`
- `--stdin` — option; optional; type `boolean`; flag
- `--evidence` — option; optional; type `text`; default ``
- `--scope` — option; optional; type `text`; default `global`
- `--scope-path` — option; optional; type `text`; default ``
- `--render-target` — option; optional; type `text`; default `root_agents`
- `--section` — option; optional; type `text`; default ``

**Example**

```bash
memoryledger memory create
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory evidence add`

Add an evidence reference to a memory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory evidence add`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--kind` — option; required; type `text`
- `--title` — option; required; type `text`
- `--uri` — option; required; type `text`
- `--reason` — option; required; type `text`
- `--excerpt` — option; optional; type `text`; default ``
- `--line-start` — option; optional; type `integer`
- `--line-end` — option; optional; type `integer`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory evidence add
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory evidence list`

List evidence references attached to a memory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory evidence list`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory evidence list
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory list`

List memory records, optionally filtered.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger memory list`

**Arguments and options**

- `--kind` — option; optional; type `text`
- `--status` — option; optional; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory list
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory set-status`

Change the lifecycle status of one memory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory set-status`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `status` — argument; required; type `text`
- `--reason` — option; required; type `text`

**Example**

```bash
memoryledger memory set-status
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory show`

Show one memory record.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory show`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--content, --no-content` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory show
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory update`

Replace the body of a memory record.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory update`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--reason` — option; required; type `text`
- `--text` — option; optional; type `text`
- `--file` — option; optional; type `path`
- `--stdin` — option; optional; type `boolean`; flag
- `--section` — option; optional; type `text`

**Example**

```bash
memoryledger memory update
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `memory validate`

Validate a memory record against all guardrails.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger memory validate`

**Arguments and options**

- `memory_id` — argument; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger memory validate
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Migrations

### `migrate apply`

Apply a migration plan.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger migrate apply`

**Arguments and options**

- `migration` — argument; optional; type `text`
- `--plan-file` — option; optional; type `path`
- `--dry-run` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger migrate apply
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `migrate cleanup`

Clean up legacy paths after successful migration.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `workspace-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger migrate cleanup`

**Arguments and options**

- `migration` — argument; optional; type `text`
- `--dry-run` — option; optional; type `boolean`; flag
- `--yes` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger migrate cleanup
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `migrate plan`

Generate a read-only migration plan.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger migrate plan`

**Arguments and options**

- `migration` — argument; optional; type `text`
- `--output, -o` — option; optional; type `path`

**Example**

```bash
memoryledger migrate plan
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `migrate recover`

Recover from a migration journal.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger migrate recover`

**Arguments and options**

- `--journal` — option; required; type `path`
- `--policy` — option; optional; type `text`; default `auto`
- `migration` — argument; optional; type `text`

**Example**

```bash
memoryledger migrate recover
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `migrate status`

Show migration status for all registered migrations.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger migrate status`

**Arguments and options**

- None.

**Example**

```bash
memoryledger migrate status
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Project

### `commands`

List all registered commands with metadata.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger commands`

**Arguments and options**

- None.

**Example**

```bash
memoryledger commands
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `doctor`

Run read-only diagnostics on project health.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger doctor`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger doctor
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `help`

Show nested help for a command path.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger help`

**Arguments and options**

- `command` — argument; optional; type `text`

**Example**

```bash
memoryledger help
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `info`

Show full read-only project inventory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger info`

**Arguments and options**

- `--paths-only, --no-paths-only` — option; optional; type `boolean`; flag
- `--no-content, --no-no-content` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger info
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `init`

Initialize a new Memoryledger project in the current directory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `workspace-write`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger init`

**Arguments and options**

- `--project-name` — option; optional; type `text`
- `--memoryledger-dir` — option; optional; type `text`; default `.memoryledger`
- `--hidden-config, --no-hidden-config` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger init
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `next-action`

Return the recommended next workflow action.

- **Audience:** `agent`
- **Stability:** `beta`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger next-action`

**Arguments and options**

- None.

**Example**

```bash
memoryledger next-action
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `status`

Show project status (initialized, memory counts, migration state).

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger status`

**Arguments and options**

- `--check, --no-check` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger status
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Rendering

### `build`

Materialize deterministic derived artifacts in the artifacts mount.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `workspace-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger build`

**Arguments and options**

- `--output, -o` — option; optional; type `path`

**Example**

```bash
memoryledger build
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `export`

Write selected generated artifacts to user/workspace destinations.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `workspace-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger export`

**Arguments and options**

- `--out` — option; optional; type `path`
- `--json` — option; optional; type `boolean`; flag
- `--backup, --no-backup` — option; optional; type `boolean`; flag
- `--include-nested, --no-include-nested` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger export
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `finalize`

Accept all candidates, build, and export in one orchestrated workflow.

- **Audience:** `agent`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger finalize`

**Arguments and options**

- `--accept-all, --accept-candidates` — option; optional; type `boolean`; flag
- `--reason` — option; optional; type `text`; default ``
- `--render, --no-render` — option; optional; type `boolean`; flag; default `True`
- `--export, --no-export` — option; optional; type `boolean`; flag
- `--json` — option; optional; type `boolean`; flag
- `--backup, --no-backup` — option; optional; type `boolean`; flag
- `--include-nested, --no-include-nested` — option; optional; type `boolean`; flag
- `--out` — option; optional; type `path`

**Example**

```bash
memoryledger finalize
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `preview`

Render without modifying authoritative or derived state.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger preview`

**Arguments and options**

- `--output, -o` — option; optional; type `text`; default `-`

**Example**

```bash
memoryledger preview
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Review

### `review accept`

Accept one or all candidate memories.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger review accept`

**Arguments and options**

- `memory_id` — argument; optional; type `text`
- `--all` — option; optional; type `boolean`; flag
- `--reason` — option; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger review accept
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `review list`

List candidate memories awaiting review.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger review list`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger review list
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `review reject`

Reject one or all candidate memories.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `memory-ref`
- **JSON:** `True`

**Usage**

`memoryledger review reject`

**Arguments and options**

- `memory_id` — argument; optional; type `text`
- `--all` — option; optional; type `boolean`; flag
- `--reason` — option; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger review reject
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Schema

### `schema list`

List available schema names.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger schema list`

**Arguments and options**

- None.

**Example**

```bash
memoryledger schema list
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `schema show`

Show field definitions for a schema.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger schema show`

**Arguments and options**

- `name` — argument; required; type `text`

**Example**

```bash
memoryledger schema show
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `schema values`

Show allowed enum values.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger schema values`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger schema values
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Storage

### `storage clear-override`

Remove a local mount override.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `workspace-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger storage clear-override`

**Arguments and options**

- `mount` — argument; required; type `text`

**Example**

```bash
memoryledger storage clear-override
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `storage set`

Set a mount's storage kind and scope.

- **Audience:** `both`
- **Stability:** `beta`
- **Effect:** `workspace-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger storage set`

**Arguments and options**

- `mount` — argument; required; type `text`
- `--storage` — option; required; type `text`
- `--storage-root` — option; optional; type `path`
- `--scope` — option; optional; type `text`; default `project`

**Example**

```bash
memoryledger storage set
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `storage validate`

Validate storage layout and bindings (read-only).

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger storage validate`

**Arguments and options**

- `--strict` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger storage validate
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `storage where`

Show complete storage topology information.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger storage where`

**Arguments and options**

- None.

**Example**

```bash
memoryledger storage where
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Templates

### `template apply`

Apply a template to create or update a memory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger template apply`

**Arguments and options**

- `template_id` — argument; required; type `text`
- `--accept` — option; optional; type `boolean`; flag
- `--reason` — option; optional; type `text`; default ``
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger template apply
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `template list`

List available global templates.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger template list`

**Arguments and options**

- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger template list
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `template remove`

Remove a template-backed memory.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger template remove`

**Arguments and options**

- `template_id` — argument; required; type `text`
- `--reason` — option; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger template remove
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `template show`

Show one template's content.

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `read`
- **Workspace:** `False`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger template show`

**Arguments and options**

- `template_id` — argument; required; type `text`
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger template show
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

### `template sync`

Sync a template (apply with optional acceptance).

- **Audience:** `both`
- **Stability:** `stable`
- **Effect:** `ledger-write`
- **Workspace:** `True`
- **Target:** `none`
- **JSON:** `True`

**Usage**

`memoryledger template sync`

**Arguments and options**

- `template_id` — argument; required; type `text`
- `--accept` — option; optional; type `boolean`; flag
- `--reason` — option; optional; type `text`; default ``
- `--json` — option; optional; type `boolean`; flag

**Example**

```bash
memoryledger template sync
```

**Related commands**

See the adjacent command group and the [workflow guide](../guides/memory-workflow).

## Automation

Use `memoryledger --json commands` for the machine-readable catalog. JSON output follows `ledgerwerk.cli.v1`.
