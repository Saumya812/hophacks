# SpacetimeDB setup

SpacetimeDB 2.10.1 is the primary database for all 12 application tables. FastAPI retains the existing HTTP API and runs external search/AI integrations. The homepage subscribes directly to the public `case_activity` table for live updates. Private case data is accessible only to the publishing backend identity.

## Restart this workspace

Run these in separate terminals from the repository root (skip a service if it is already running):

```bash
bash scripts/spacetime.sh start
```

```bash
cd backend
.venv/bin/uvicorn main:app --reload --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://localhost:5173. Database readiness is at http://127.0.0.1:8000/health/database. SpacetimeDB listens on port 3000. Its persistent data and local publishing identity are in the ignored `.spacetime/` directory: retain this directory across restarts.

## Fresh checkout

Install the official CLI locally, then install the module dependencies:

```bash
curl -sSf https://install.spacetimedb.com -o /tmp/install-spacetime.sh
sh /tmp/install-spacetime.sh --root-dir "$PWD/.spacetime" -y
cd spacetimedb/spacetimedb
npm ci
```

From the repository root, start the server using the command above. In another terminal publish the module:

```bash
bash scripts/spacetime.sh publish
bash scripts/spacetime.sh generate
```

Copy `backend/.env.example` to `backend/.env`. Set `SPACETIMEDB_URI=http://127.0.0.1:3000`, `SPACETIMEDB_DATABASE=findmypal`, and set `SPACETIMEDB_TOKEN` to the local publisher's `spacetimedb_token` value in `.spacetime/config/cli.toml`. Keep that value secret; never add it to a frontend variable. Install Python dependencies in `backend/.venv` and run `npm ci` in `frontend`. Copy `frontend/.env.example` to `frontend/.env`.

The publisher identity is recorded when a database is first created. Publishing with a different identity does not grant that identity backend access. Back up the local identity along with the database. Module publication explicitly forbids deleting existing data.

## Existing data

The current workspace's original data was copied and verified: 1 user, 2 cases, and 4 sightings. A private backup is stored in `backend/.migration_backups/20260919T202147Z.json`. The original Supabase project was left intact.

For a new migration, pause application writes, temporarily supply `SUPABASE_URL` and `SUPABASE_KEY` in the backend environment, then run:

```bash
backend/.venv/bin/python scripts/migrate_to_spacetime.py
```

Only this export script reads legacy credentials. It saves a private backup, imports native rows, and checks their values. Replaying a backup uses upserts and can overwrite newer destination values, so use it only during a controlled migration. Historical `db/schema.sql` and `db/migrations/` files are retained as references; they are not used at runtime.

## Verification

Publish a separate test database before running integration tests:

```bash
bash scripts/spacetime.sh publish findmypal-test
cd backend
RUN_SPACETIME_TESTS=1 SPACETIMEDB_DATABASE=findmypal-test .venv/bin/python -m unittest discover -s tests -v
```

From the repository root, verify actual anonymous WebSocket delivery:

```bash
frontend/node_modules/.bin/esbuild scripts/test_spacetime_live.ts --bundle --platform=node --format=esm --outfile=/tmp/findmypal-live-test.mjs
node /tmp/findmypal-live-test.mjs
```

The tests use `findmypal-test`, never the application's database. The native module enforces transaction rollback, parent references, unique watchers, atomic engagement counts, and retry receipts. Receipts are retained for 24 hours; replaying a write after that window is not guaranteed idempotent.

## Deployment

This setup runs locally. For hosting, publish the module on the chosen SpacetimeDB server using the deployment backend identity; configure FastAPI's URI/database/token and the frontend's public `VITE_SPACETIMEDB_URI`/`VITE_SPACETIMEDB_DATABASE`, then rebuild the frontend. Use HTTPS/WSS endpoints. SpacetimeDB procedure APIs are version-sensitive, so keep the CLI, server and SDK versions aligned and run these tests before upgrading.

External AI/scraping API keys and their availability still affect those features. Email remains a persisted outbox log until an email provider is configured. Existing mock-user and owner-token behavior is preserved; this migration does not introduce a full account system.
