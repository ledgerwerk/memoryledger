---
id: memory-0004
kind: rule
title: Operating principles
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

- Prefer the smallest correct change.
- Preserve memory review semantics before convenience.
- Preserve deterministic and safe generated output.
- Keep changes in the owning layer.
- Avoid speculative abstractions, broad rewrites, unrelated formatting, casual contract changes, migration code unless requested, and commits.
