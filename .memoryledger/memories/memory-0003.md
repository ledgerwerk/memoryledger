---
id: memory-0003
kind: rule
title: Communication
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

- Assume the user is technically strong.
- Be direct, concrete, and brief.
- Do not explain obvious Python, Typer, YAML, pytest, ruff, mypy, or packaging basics.
- Do not narrate trivial edits.
- Ask a clarifying question only when ambiguity could change memory policy, review semantics, file safety, or CLI contracts.
- Otherwise, proceed with the smallest correct change.
- Report results as: changed, verified, not verified, risks.
