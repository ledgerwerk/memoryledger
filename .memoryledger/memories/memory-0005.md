---
id: memory-0005
kind: rule
title: Durable state invariants
status: accepted
priority: 100
scope: global
scope_path: ""
render_target: root_agents
source: cli
created_version: 2
modified_version: 2
tags: []
origin: ""
origin_hash: ""
section: ""
---

- Treat `.memoryledger/` as durable project state.
- Each memory lives in `.memoryledger/memories/memory-NNNN/`.
- `memory.yaml`, `content.md`, `evidence.md`, and `versions/` are canonical memory records.
- Accepted memory must have evidence or a review reason.
- Candidate memory is not rendered by default.
- Rendered files must contain the generated marker.
- Manual files without the generated marker must not be overwritten by export.
- Scope paths must remain repo-relative and must not escape the workspace.
