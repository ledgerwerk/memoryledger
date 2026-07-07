---
id: memory-0001
kind: semantic
title: Project contract
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

`memoryledger` is a Python CLI and library for auditable long-term project memory and deterministic `AGENTS.md` rendering. Its core contract is: capture memory as durable candidate records, require explicit review before acceptance, render only reviewed memory by default, and export generated agent files safely.

Canonical workflow:

```text
init -> memory create -> review accept -> render -> export
```

This workflow is the product contract, not decoration.
