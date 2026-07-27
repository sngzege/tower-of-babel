# SAVE SYSTEM

> **Status:** infrastructure IMPLEMENTED (autonomous pre-production); payloads are empty until gameplay systems own them. Complies with RULES.md §18 (versioned saves, migrations, never silently invalidate).

## 1. Persistence Model

One save file = three top-level sections (`src/save/save_schema.py`):

```yaml
meta:        {save_version: 1, created_at: ..., updated_at: ...}
persistent:  {}     # everything that survives between runs
run_state:   null   # the in-progress run, or null when no run is active
```

| Section | Owned by (planned) | Contains (planned, PROVISIONAL) |
|---------|--------------------|---------------------------------|
| `persistent` | progression + village systems | hero progression, class mastery, village state, NPC tracks, unlocks, depth records, settings mirrors |
| `run_state` | run system | seed, stage/depth, build state, carried resources, run flags |

Why the split matters for open decisions:

- **D4 (extraction):** a run can end with `EXTRACTED` and bank results into `persistent` — or never exist mid-run at all. Both models fit.
- **D5 (death penalty):** the penalty is a rule about *what moves* from `run_state` to `persistent` — the format doesn't care.
- **D15 (mid-run save):** `run_state` nullable = "no suspended run" is always representable.

## 2. Versioning and Migrations

- `core.constants.SAVE_VERSION` is the single source of truth (currently **1**).
- `src/save/migrations.py` — `MigrationRegistry`: `register(from_version, fn)` upgrades one version step; `migrate()` chains steps up to current.
- **Newer save than supported → load is refused with a clear error.** Never silently invalidated (RULES.md §18).
- Adding a migration when the schema changes is part of the definition of done for any change touching save payloads.

## 3. Integrity and Failure Policy

- Writes are **atomic** (temp file + `os.replace` via `utils.file_utils.write_text_atomic`) — a crash cannot leave a truncated save.
- `SaveManager.write()` validates structure before writing; `read()` validates after loading, then migrates.
- YAML storage for debuggability during development (binary packing is a release-phase option, not now).
- Default slot: `saves/save_1.yaml` (slot id from `config/game.yaml`).

## 4. Test Coverage (tests/unit/test_save_system.py)

Template validity · missing-key reporting · write/read roundtrip · invalid-write refusal · missing-file error · read-or-new fallback · newer-version refusal · migration chain. **Not yet executed** (no interpreter in the preparation environment — see SETUP.md).
