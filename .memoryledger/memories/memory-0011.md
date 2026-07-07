---
id: memory-0011
kind: rule
title: Code style
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

- Follow existing style first.
- Keep functions focused.
- Prefer explicit names over clever compression.
- Add type hints for new or changed public functions.
- Keep public error codes stable unless explicitly changing the contract.
- Avoid new dependencies unless explicitly requested.
- Do not reformat unrelated files.
- Do not rename public symbols without a strong reason.
- Do not use git commands that create commits or rewrite history.
