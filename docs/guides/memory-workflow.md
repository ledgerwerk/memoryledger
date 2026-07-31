# Memory workflow

Use the record lifecycle as the unit of work:

```bash
# Create multiline content safely.
memoryledger memory create --kind procedure --title "Run tests" --stdin <<'EOF'
Run the focused tests before the full suite.
EOF

memoryledger memory list
memoryledger memory show memory-0001 --content
memoryledger memory update memory-0001 --stdin --reason "Clarified the procedure." <<'EOF'
Run focused tests, then run the full suite.
EOF
memoryledger memory append memory-0001 --stdin --reason "Added a note." <<'EOF'
Record failures as evidence.
EOF
memoryledger memory validate memory-0001
memoryledger memory evidence add memory-0001 --kind command --title "Test run" \
  --uri "command:pytest" --reason "The command verifies the procedure."
memoryledger review accept memory-0001 --reason "User approved this procedure."
memoryledger preview
memoryledger build
memoryledger export
```

Use `review reject` or `memory archive` when appropriate. Use `finalize` when
the explicit acceptance reason and export policy are already known. Prefer
single-quoted heredoc bodies for shell examples; `--text` is convenient for
short text but shell expansion and quoting can alter sensitive or multiline
content.
