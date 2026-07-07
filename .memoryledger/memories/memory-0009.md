---
id: memory-0009
kind: rule
title: Rendering and export contract
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

- Rendering must be deterministic and safe.
- Preserve accepted-only rendering by default, configured sort order, root section names, linked document behavior, nested `AGENTS.md` behavior, generated markers, max output size validation, `.memoryledger/rendered/`, configured export paths, and manual-file overwrite protection.
- Keep root `AGENTS.md` concise. Move long procedure, semantic, episode, or document memory to linked documents when appropriate.
