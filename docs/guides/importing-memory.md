# Importing memory

Text, run HTML, and current-run import paths create candidates and preserve
provenance:

```bash
memoryledger import text --stdin <<'EOF'
The focused test suite must pass before the full suite.
EOF
memoryledger import run-html --file run.html
memoryledger import current-run
```

Run HTML and current-run intake are controlled by config feature flags. Import
metadata identifies the source and uses safe excerpts. Transcript-like input,
secret-like values, and oversized raw transcripts are rejected. Imported
records still require explicit review before rendering.
