For each task:

1. identify the owned layer
2. make the smallest coherent change
3. add or update focused tests
4. run the narrowest useful verification
5. widen verification only when the change crosses layers

Focused examples:

- memory validation bug: `memoryledger/guardrails.py` plus guardrail or memory tests
- review transition bug: `memoryledger/review.py` or `memoryledger/storage.py` plus review tests
- render output bug: `memoryledger/render.py` plus render tests
- CLI contract bug: `memoryledger/cli.py` plus CLI or JSON contract tests
- config discovery bug: `memoryledger/storage.py` plus config discovery tests
- import behavior bug: `memoryledger/intake.py` plus import tests

Start narrow. Expand only when needed.

```bash
pytest tests/test_memory_review.py
pytest tests/test_render_agents.py
pytest
ruff check .
ruff format --check .
mypy memoryledger
```

Run `ruff check` when touching Python code. Run `mypy memoryledger` when changing typed public or core logic. Run skill or docs tests when touching `skills/memoryledger/SKILL.md`, docs, examples, or CLI command behavior.
