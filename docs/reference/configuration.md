# Configuration

The canonical project configuration is `.ledger/memoryledger/config.toml`,
version 2. Global defaults are read from
`$XDG_CONFIG_HOME/ledger/memoryledger.toml` or
`~/.config/ledger/memoryledger.toml`. Project values override global values by
section. Unknown fields are rejected.

## Top-level and section fields

| Section             | Fields                                                                                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| top level           | `config_version`, `ledger`, `render`, `intake`, `template_policy`                                                                                        |
| `[ledger]`          | `code`, `version`                                                                                                                                        |
| `[render]`          | `root_agents_path`, `linked_docs_dir`, `nested_agents_enabled`, `linked_docs_enabled`, size limits, inclusion flags, `evidence_index_path`, `sort_order` |
| `[intake]`          | `allow_run_html`, `allow_current_run`, `default_review_status`                                                                                           |
| `[template_policy]` | `enabled`, `ids`, `auto_accept`                                                                                                                          |

The rendered default is:

```toml
config_version = 2

[ledger]
code = "ml"
version = 0

[render]
root_agents_path = "AGENTS.md"
linked_docs_dir = "agent_docs"
nested_agents_enabled = false
linked_docs_enabled = true
max_root_agents_chars = 12000
max_linked_doc_chars = 50000
include_local = false
include_rejected = false
include_evidence = false
evidence_index_path = ""
sort_order = ["rule", "procedure", "semantic", "learning", "episode", "document"]

[intake]
allow_run_html = true
allow_current_run = true
default_review_status = "candidate"

[template_policy]
enabled = false
ids = []
auto_accept = false
```
