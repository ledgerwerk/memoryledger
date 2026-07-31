# Schemas and values

Use the CLI to inspect the runtime schema inventory:

```bash
memoryledger schema list
memoryledger schema show memory
memoryledger schema values
```

Memory kinds are `rule`, `learning`, `episode`, `procedure`, `semantic`,
`document`, and `local`. Statuses are `candidate`, `accepted`, `rejected`, and
`archived`; scopes are `global`, `repo`, `directory`, `file`, `command`,
`workflow`, and `local`; render targets are `root_agents`, `linked_doc`,
`nested_agents`, and `none`. Evidence kinds are `file`, `config`, `run`,
`command`, `user_approval`, and `external`.

Accepted input aliases include `project -> repo` and
`package-workflow -> procedure` (also accepted with an underscore). The CLI
normalizes aliases before validation and serializes canonical values.
