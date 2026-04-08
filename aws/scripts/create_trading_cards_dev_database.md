# Create `trading_cards_dev` on RDS (same instance as prod)

**Default:** from the repo root, with **`DATABASE_URL`** in `backend/.env` pointing at your prod (or any) DB on that instance:

```bash
python3 migrate.py --dev
```

That connects via **`postgres`** / **`template1`**, runs **`CREATE DATABASE trading_cards_dev`** if needed (when your DB user has permission), then applies **`schema.sql`** on a fresh DB (no **`cards`** table yet), then all **`migration_*.sql`** files. Use **`--no-create-dev-db`** if you create the DB manually.

---

Manual SQL (e.g. if `CREATE DATABASE` is denied to the app user): connect as a role that can create databases, to **`postgres`**:

```sql
CREATE DATABASE trading_cards_dev;
```

If your app user is not the owner, grant access (adjust `appuser`):

```sql
GRANT ALL PRIVILEGES ON DATABASE trading_cards_dev TO appuser;
```

Then from the repo (with `DATABASE_URL_DEV` in `backend/.env` pointing at `.../trading_cards_dev`):

```bash
python3 migrate.py --dev
```

Apply the same migrations to prod DB with `migrate.py --rds` or `--both` as you already do.
