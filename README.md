# memoryledger

Auditable long-term project memory ledger for coding agents.

`memoryledger` stores durable, reviewable, retrievable project memory across
sessions without polluting task, plan, architecture, or specification ledgers.
It is built on the sibling [`ledgercore`](../ledgercore) library.

- Package: `memoryledger`
- Primary CLI: `memoryledger`
- Short CLI alias: `memledger`
- Config file: `.memoryledger.toml`
- State directory: `.memoryledger/`
- Default export: `.memoryledger/exports/AGENTS.memory.md`

## Install (development)

```bash
python -m pip install -e ".[dev]"
```

## CLI (MVP)

```bash
memoryledger init
memoryledger capture --type procedural --title "Ledger discovery rule" --body ./note.md
memoryledger list
memoryledger list --status candidate
memoryledger accept mem-YYYYMMDD-0001
memoryledger reject mem-YYYYMMDD-0001
memoryledger search "ledger discovery"
memoryledger context "create a new ledger tool"
memoryledger export --target agents-md
memoryledger doctor
memledger context "fix pytest CI"
```

## Product rule

Agents may propose memory. Only the user, or an explicit approval command,
promotes memory to accepted project memory. This prevents silent memory drift
while still allowing the project to accumulate durable, reviewable, retrievable
agent memory.
