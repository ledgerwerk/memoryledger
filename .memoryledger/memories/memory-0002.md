---
id: memory-0002
kind: semantic
title: Important code surfaces
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

Use the owning layer before editing:

- `memoryledger/cli.py`: Typer command tree, human output, JSON output, and error mapping
- `memoryledger/models.py`: dataclasses, allowed kinds, statuses, scopes, render targets, and render config defaults
- `memoryledger/storage.py`: config discovery, workspace initialization, durable record layout, IDs, status updates, and content versions
- `memoryledger/review.py`: review transition rules and acceptance validation
- `memoryledger/render.py`: root, linked, nested rendering, generated output validation, rendered writes, and export behavior
- `memoryledger/guardrails.py`: content, scope, generated text, and overwrite safety rules
- `memoryledger/intake.py`: import candidate extraction
- `memoryledger/errors.py`: public error type and codes
- `memoryledger/launcher.py`: console entrypoint
- `skills/memoryledger/SKILL.md`: external agent workflow contract
- `tests/`: CLI, storage, render, review, guardrail, import, nested agent, and skill contract tests
