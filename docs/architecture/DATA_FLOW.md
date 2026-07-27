# DATA FLOW

> **Status:** FIRST DRAFT (autonomous pre-production). Defines the data-driven content pipeline (RULES.md §7). All schemas are **PROVISIONAL** — they constrain structure, never creative content. Design decisions D1-D15 remain open.

## 1. The Pipeline

```text
data/<category>/**.yaml          (authored content - human-approved only)
        ↓  core.data_loader      (YAML -> DataDocument{category, document, source})
        ↓  schema validation     (tools/data_validation - offline, + dev-time hooks)
        ↓  core.content_registry (id index, tag queries, duplicate detection, freeze)
        ↓  game systems          (factories build runtime objects from documents)
        ↓  runtime state         (run state / persistent state -> save system)
```

Rules:

- Systems **never** read YAML directly; they query the registry by id/tag.
- The registry is loaded and validated at bootstrap, then **frozen** before a run starts.
- Ids are strings (`^[a-z][a-z0-9_]*$`), unique per category. Cross-references (`ability_ids`, `boss_id`, ...) are plain id strings; referential integrity is checked by the validator tooling (current release: structural checks; reference resolution checks are the planned next tooling step).
- Balance numbers live in data, never in code (RULES.md §8).

## 2. Content Categories

| Category (directory) | Schema (`data/schemas/`) | Status |
|----------------------|--------------------------|--------|
| `data/player/` | player.schema.yaml | provisional |
| `data/classes/` | class.schema.yaml | **new (provisional)** |
| `data/abilities/` | ability.schema.yaml | **new (provisional)** |
| `data/passives/` | passive.schema.yaml | **new (provisional)** |
| `data/weapons/` | weapon.schema.yaml | provisional |
| `data/items/` (+ `equipment/`) | item.schema.yaml / equipment.schema.yaml | provisional |
| `data/enemies/` (+ `bosses/`) | enemy.schema.yaml / boss.schema.yaml | provisional |
| `data/loot/` | loot_table.schema.yaml | provisional |
| `data/world/rooms/` | room.schema.yaml | provisional |
| `data/world/stages/` | stage.schema.yaml | **new (provisional)** |
| `data/npcs/` | npc.schema.yaml | **new (provisional)** |
| `data/village/buildings/` | building.schema.yaml | **new (provisional)** |
| `data/village/upgrades/` | village_upgrade.schema.yaml | **new (provisional)** |
| `data/unlocks/` | unlock.schema.yaml | **new (provisional)** |
| `data/progression/` | progression.schema.yaml | provisional |
| `data/localization/` | (no schema yet) | strings land after design approval |

Second-level folders with their own schema (items/equipment, enemies/bosses, world/rooms, village/upgrades) are mapped in `tools/data_validation/validate_data.py` (`SCHEMA_OVERRIDES`).

## 3. Schema Format

A schema is a YAML file: `{schema: <name>, version: <int>, fields: {...}, example: {...}}`.

Field rules (all optional unless noted): `type` (str/int/float/bool/list/dict) · `required` · `default` · `pattern` (str) · `enum` · `min`/`max` (numbers) · `min_length`/`max_length` (str/list) · `item` (rules for list elements) · `keys` (rules for dict members). Shorthand: a plain string means `{type: <string>}` (e.g. `item: str`).

- `bool` is **not** an `int`; `float` accepts ints.
- Every schema carries an `example:` document that must validate against itself — enforced by test `test_shipped_schemas_validate_their_own_examples` and by the CLI.
- Schema evolution: bump `version`, migrate content files in the same commit, note it in CHANGELOG.md.

## 4. Adding New Content (the everyday workflow)

Example: a new enemy, **after** the human developer approves it:

1. Create `data/enemies/common/<id>.yaml` with an `id`, `name`, and fields per `enemy.schema.yaml`.
2. Run `python scripts/validate_data.py` — must pass (structure, types, embedded examples).
3. Done: the registry discovers the file at bootstrap; factories can build it by id. **No code changes.**

Adding a **new category**: schema in `data/schemas/` → entry in `CATEGORY_SCHEMAS` (and `SCHEMA_OVERRIDES` if nested) in `tools/data_validation/validate_data.py` → data directory → register the category at bootstrap (`src/main.py CONTENT_CATEGORIES`).

## 5. Conventions

- **Comments are free, content is not:** YAML files may carry comment lines, but every content field requires design approval (RULES.md §3, §9).
- **Placeholder files:** comment-only files are placeholders; the validator skips them (they are not errors).
- **Tags** are the synergy vocabulary (GAMEPLAY_DESIGN.md §19): lowercase snake_case; adding a tag to the vocabulary is a design decision; using an existing tag is content work.
- **No magic values in code** (RULES.md §8): if a number affects gameplay, it belongs in a data file.
- **Localization:** user-facing strings eventually resolve through `data/localization/` (en.yaml is a placeholder); content files store string *ids* once localization is wired (deferred — not needed for the vertical slice greybox).

## 6. Validation Layers

| Layer | Tool | When |
|-------|------|------|
| Offline CLI | `python scripts/validate_data.py` | before every commit touching data/ |
| Unit tests | `tests/unit/test_schema_validator.py` (+ shipped-schema examples) | every test run |
| Dev-time hook | `ContentRegistry.add_validator(...)` (wire schema checks via `config/development.yaml: data.validate_on_load`) | at bootstrap during development |
| CI (future) | same CLI in a pipeline | when CI is set up |

