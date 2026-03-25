# Manual / exploratory scripts

These files were moved from `backend/test_*.py` so they are **not** confused with the **pytest** suite under `tests/` (see `pytest.ini`).

- Run from repo root with `PYTHONPATH=.` or `python3 scripts/dev/<name>.py` after `cd` to repo root as needed.
- They may call live APIs, localhost, or require `.env` — **not** run in CI.

**CI tests:** `pytest tests/` (unit → integration → qa in `.github/workflows/qa.yml`).
