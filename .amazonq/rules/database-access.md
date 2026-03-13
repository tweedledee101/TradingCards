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
