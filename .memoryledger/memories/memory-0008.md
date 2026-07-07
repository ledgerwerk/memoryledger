---
id: memory-0008
kind: rule
title: Guardrails
status: accepted
priority: 100
scope: global
scope_path: ""
render_target: root_agents
source: cli
created_version: 3
modified_version: 3
tags: []
origin: ""
origin_hash: ""
section: ""
---

- Preserve rejection of empty content, secret-like values, unresolved placeholders, huge transcript-like content, invalid enum values, invalid scope paths, generated output without the marker, generated output containing raw run HTML references, and manual file overwrites during export.
