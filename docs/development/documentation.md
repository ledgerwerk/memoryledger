# Documentation maintenance

Author pages in MyST Markdown. Use headings consistently, fenced code blocks
with a language, relative Markdown links for pages, and `toctree` directives
for navigation. Keep normative claims tied to the source modules and tests
listed in the implementation brief.

The CLI page is generated; update `command_catalog.py`, Typer help, or the
generator and run:

```bash
python docs/_scripts/generate_cli_reference.py
python docs/_scripts/generate_cli_reference.py --check
```

Add a new page to the relevant group index and keep warning-as-error builds
clean. Do not hide broken references by disabling `nitpicky`.
