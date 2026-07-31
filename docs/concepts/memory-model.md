# Memory model

A memory has a stable identifier such as `memory-0001`. The identifier is
allocated from storage metadata, not from timestamps. Supported kinds are
`rule`, `learning`, `episode`, `procedure`, `semantic`, `document`, and `local`.
Scopes are `global`, `repo`, `directory`, `file`, `command`, `workflow`, and
`local`. Render targets are `root_agents`, `linked_doc`, `nested_agents`, and
`none`.

Records also carry a priority (default `100`), title, content, source, origin,
tags, and optional section. `created_version` and `modified_version` identify
the ledger versions that created and last changed the record. Version numbers
are deterministic ledger history references; timestamps are unsuitable as
identity or ordering keys. Git is the history for changes rather than a
per-record snapshot directory.

Memory content is Markdown with YAML front matter. A representative record is:

```markdown
---
id: memory-0001
kind: rule
title: Use plans
status: candidate
priority: 100
scope: repo
scope_path: ""
render_target: root_agents
source: cli
created_version: 1
modified_version: 1
tags: [workflow]
origin: ""
section: ""
evidence_refs: []
---

Always create and review a plan before implementation.
```

The storage serializer remains authoritative for exact field names and defaults.
