# DEVELOPMENT SETUP

> Environment guide. Tested command list for a fresh machine (the pre-production environment had **no Python, uv, or git installed** — start at step 1).

## 1. Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.11+ | primary language (pyproject.toml `requires-python`) |
| uv | latest | dependency + environment management (IMPLEMENTATION_PLAN tooling choice) |
| git | latest | version control (RULES.md §19) |

Install examples (Windows): `winget install Python.Python.3.12`, `winget install astral-sh.uv`, `winget install Git.Git`.

## 2. First-Time Setup

```powershell
cd <project-root>
git init                       # if not already a repository
uv sync                        # creates .venv, installs pyyaml + dev tools (pytest, ruff, mypy)
uv lock                        # only needed to regenerate uv.lock after dependency changes
```

## 3. Everyday Commands

| Task | Command |
|------|---------|
| Run the app (bootstrap skeleton) | `uv run python scripts/run.py` |
| Run all tests | `uv run python scripts/test.py` |
| Validate data files | `uv run python scripts/validate_data.py` |
| Lint | `uv run ruff check src tests tools scripts` |
| Format | `uv run ruff format src tests tools scripts` |
| Type check | `uv run mypy src` |

(Plain `python` instead of `uv run python` works inside an activated `.venv`.)

## 4. First Verification After Setup

Run these **in order** on a fresh setup (all verified passing as of 2026-07-27):

1. `uv run python scripts/test.py` — expect ~55 passed; **report any failure before writing new code.**
2. `uv run python scripts/validate_data.py` — expect `Data validation OK (... placeholder file(s) skipped).`
3. `uv run python scripts/run.py` — expect bootstrap logs ending with "engine not implemented yet".

## 5. Troubleshooting

- **`python` not found:** use `uv run python` (uv manages its own interpreter) or add Python to PATH; the WindowsApps `python.exe` alias is a Store stub, not an interpreter.
- **Import errors in tests:** run from the repository root; `pyproject.toml` sets `pythonpath = ["src"]`.
- **YAML errors:** PyYAML is the only runtime dependency; if it is missing, run `uv sync`.
