# Database Access Rule

## PostgreSQL Commands

**ALWAYS use `sudo -u postgres` when running psql commands in this project.**

### Correct Usage:
```bash
sudo -u postgres psql -d trading_cards -c "SELECT * FROM cards;"
```

### Incorrect Usage (will fail):
```bash
psql -U postgres -d trading_cards -c "SELECT * FROM cards;"
```

## Reason
This project uses peer authentication for PostgreSQL, requiring sudo access to the postgres user.

## RDS / `trading_cards_dev` (TCP URL)

If **`DATABASE_URL_DEV`** is not set in `backend/.env`, **`migrate.py --dev`** still works by deriving the dev URL from **`DATABASE_URL`** — but your shell will not have **`DATABASE_URL_DEV`**, so **`psql "$DATABASE_URL_DEV"`** connects to nothing useful.

Use:

```bash
python3 scripts/psql_dev.py -c '\d cards'
```

Or add an explicit line to `backend/.env`: `DATABASE_URL_DEV=postgresql://…/trading_cards_dev`, then `source backend/.env` and `psql "$DATABASE_URL_DEV" …`.
