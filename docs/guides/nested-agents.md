# Nested `AGENTS.md`

Set `nested_agents_enabled = true` in the project render configuration. A
memory with a directory scope and `scope_path` such as `src/package` may use
the `nested_agents` render target. Include nested output explicitly when
exporting:

```bash
memoryledger export --include-nested
```

Paths are confined to the project root and cannot escape through `..` or an
absolute path. This is useful for package-specific instructions while keeping
the root file concise. Nested output is disabled by default.
