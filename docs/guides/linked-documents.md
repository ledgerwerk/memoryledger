# Linked documents

The default linked-document directory is `agent_docs`. Long accepted content
can be placed there when the root threshold would be exceeded. The kind and
configured section determine document placement; exact mapping is stable only
through the renderer and config.

Generated documents carry the Memoryledger marker and are protected from direct
edits. Files without the marker remain manual. The `linked-docs-dir` migration
can move the legacy `docs/agents` directory through the migration framework;
manual copying is not a substitute for its ownership and journal checks.
