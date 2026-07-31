# Rendering

Canonical memory records are authoritative. `AGENTS.md`, linked documents,
and nested `AGENTS.md` files are derived artifacts with a generated ownership
marker. The root document contains concise sections; content beyond configured
thresholds is placed in linked documents when the target and configuration
allow it.

Rendering is deterministic: eligible statuses and scopes are filtered first,
then records are sorted by configured kind order and stable record fields.
Root and linked-document size limits are validated before output is written.
Manual files are never overwritten. `--backup` preserves an already generated
file before replacement but does not grant permission to overwrite a manual
target; adoption is the explicit workflow for converting a manual file.

`preview` returns derived text, `build` materializes artifacts in the cache
mount, and `export` writes configured user/workspace destinations. These stages
are separate so inspection cannot accidentally mutate durable output.
