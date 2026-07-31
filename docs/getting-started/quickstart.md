# Quickstart

Memory enters the ledger as a candidate and becomes renderable only after an
explicit review transition.

```bash
memoryledger init

cat <<'EOF' | memoryledger memory create \
  --kind rule \
  --title "Use plans" \
  --scope repo \
  --stdin
Always create and review a plan before implementation.
EOF

memoryledger review accept memory-0001 \
  --reason "User approved the project rule."

memoryledger preview
memoryledger build
memoryledger export
```

For an agent-oriented batch workflow:

```bash
memoryledger finalize \
  --accept-all \
  --reason "User approved the candidate memories." \
  --export
```

`preview` renders without materializing artifacts, `build` writes deterministic
artifacts to the resolved cache mount, `export` writes selected owned targets,
and `finalize` orchestrates review, build, and optional export.
