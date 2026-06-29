# memoryledger

`memoryledger` is an auditable long-term project memory ledger and deterministic `AGENTS.md` renderer.

## Quick start

```bash
memoryledger init
memoryledger memory create --kind rule --title "Use plans" --text "Always plan before implementation."
memoryledger review accept memory-0001 --reason "User approved project rule."
memoryledger render --print
memoryledger export
```

The short alias `memledger` exposes the same CLI.
