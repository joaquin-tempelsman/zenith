# Schema Migration Workflow

When you modify the `Item` model in `src/database/models.py`, existing per-user databases won't pick up the change automatically — you need to create an Alembic migration.

## Steps

1. **Edit the model** in `src/database/models.py`

2. **Generate the migration**
   ```bash
   uv run alembic revision --autogenerate -m "describe your change"
   ```

3. **Review the generated file** in `alembic/versions/` — verify the `upgrade()` and `downgrade()` functions are correct. Alembic can misdetect renames as drop+add, so always check.

4. **Commit & push** — the migration file must be in git.

On the next deploy (or local restart), `run_migrations()` in `startup_event` applies pending migrations to all existing `inventory_*.db` files automatically. New users created after the deploy get the updated schema from `create_all()`.

## Rollback

```bash
uv run alembic downgrade -1
```

This reverts the last migration across all discovered databases.

## Notes

- **New tables** (e.g., in `MetadataBase`) don't need migrations — `create_all()` handles those.
- **Column changes on existing tables** (add/rename/drop/retype on `items`) always need a migration.
- Migrations use `render_as_batch=True` because SQLite doesn't support `ALTER TABLE DROP COLUMN` natively.
