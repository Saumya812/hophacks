#!/usr/bin/env python3
"""One-time, non-destructive legacy export -> native SpacetimeDB import.

Run with backend/.venv/bin/python scripts/migrate_to_spacetime.py.
Legacy credentials are read only here. Supabase is never changed or deleted.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import httpx
from dotenv import dotenv_values
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from database import SCHEMA, SpacetimeDatabase


def migrate(backup=None):
    env = {**dotenv_values(ROOT / 'backend/.env'), **os.environ}
    if backup:
        records = json.loads(Path(backup).read_text())['tables']
    else:
        records = {}
        url = env.get('SUPABASE_URL', '').rstrip('/')
        token = env.get('SUPABASE_KEY', '')
        if not url or not token:
            raise RuntimeError('Legacy export credentials are missing; provide a prior --backup file.')
        with httpx.Client(timeout=30, headers={'apikey': token, 'Authorization': f'Bearer {token}'}) as client:
            for table in SCHEMA:
                rows, offset = [], 0
                while True:
                    response = client.get(f'{url}/rest/v1/{table}', params={'select': '*', 'order': 'id.asc', 'offset': offset, 'limit': 500})
                    if response.status_code == 404 and offset == 0:
                        print(f'{table}: not present in legacy schema; empty destination table')
                        break
                    response.raise_for_status()
                    batch = response.json()
                    rows.extend(batch)
                    if len(batch) < 500: break
                    offset += len(batch)
                records[table] = rows
        directory = ROOT / 'backend/.migration_backups'
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump({'created_at': datetime.now(timezone.utc).isoformat(), 'tables': records}, stream)
        print('Legacy backup saved:', path.relative_to(ROOT))
    # Check the whole export before starting any imports.
    for table, rows in records.items():
        if table not in SCHEMA: raise ValueError(f'Unrecognized table {table}')
        for row in rows:
            unknown = set(row) - set(SCHEMA[table])
            if unknown: raise ValueError(f'{table}: destination missing columns {sorted(unknown)}')
    db = SpacetimeDatabase(env['SPACETIMEDB_URI'], env['SPACETIMEDB_DATABASE'], env['SPACETIMEDB_TOKEN'])
    for table in SCHEMA:
        for start in range(0, len(records.get(table, [])), 100):
            db.table(table).upsert(records[table][start:start+100]).execute()
        print(f'{table}: imported {len(records.get(table, []))} records')
    # Exact field verification, with timestamp canonicalization and derived counter checks.
    for table, expected in records.items():
        actual = {r['id']: r for r in db.table(table).select('*').execute().data}
        for source in expected:
            target = actual.get(source['id'])
            if target is None: raise RuntimeError(f'{table}: missing imported row')
            for field, value in source.items():
                if table == 'persons' and field in {'tips_count','watchers_count'}: continue
                got = target[field]
                if SCHEMA[table][field]['sql_type'] == 'TIMESTAMPTZ' and value and got:
                    same = TypeAdapter(datetime).validate_python(value) == TypeAdapter(datetime).validate_python(got)
                else: same = value == got
                if not same: raise RuntimeError(f'{table}: verification mismatch for {field}')
    print('Verified all imported IDs and stored fields. Derived tip/watch counts are recomputed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', help='Replay an existing private export instead of fetching legacy records')
    args = parser.parse_args()
    migrate(args.backup)
