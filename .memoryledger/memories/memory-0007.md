---
id: memory-0007
kind: rule
title: Memory and review contract
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

- Preserve deterministic `memory-NNNN` IDs from storage metadata.
- Preserve default status `candidate` and default priority `100`.
- Preserve durable `content.md`, optional `evidence.md`, and first version records under `versions/`.
- Review transitions require a reason.
- Accepted memory must be validated before status update.
- Valid statuses are `candidate`, `accepted`, `rejected`, and `archived`.
- Do not allow unreviewed candidate memory to appear in generated output by default.
