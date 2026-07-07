---
id: memory-0006
kind: rule
title: CLI contract
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

- Preserve registered command families: `init`, `status`, `doctor`, `info`, `memory`, `review`, `render`, `export`, `agents`, and `import`.
- Keep `memledger` as an alias for the same launcher.
- Do not casually change command names, option names, exit codes, or human output that tests may rely on.
- `--json` output is a machine-readable contract. Test payload shape when changing it.
- Error output should preserve structured `MemoryledgerError` codes where applicable.
