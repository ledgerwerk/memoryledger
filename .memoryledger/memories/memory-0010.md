---
id: memory-0010
kind: rule
title: Docs and skill rules
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

- Docs, examples, and skill files must agree.
- When changing commands or workflow behavior, update `README.md`, `skills/memoryledger/SKILL.md`, and tests that validate skill files or CLI examples as needed.
- Do not document commands that are not registered.
- Do not leave examples using removed options or aliases.
