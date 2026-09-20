"""SpacetimeDB repository used by every backend feature.

The fluent query builder preserves existing route behavior while execute_query
runs validation, filtering and writes inside a native SpacetimeDB transaction.
No application data is stored in this process or in a fallback database.
"""
from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.parse import quote

import httpx
from config import get_settings

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / 'db' / 'spacetime_schema.json').read_text())


class DatabaseError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class QueryResult:
    data: list
    count: int = 0


class SpacetimeDatabase:
    def __init__(self, uri: str, database: str, token: str, *, client=None):
        self.uri = uri.rstrip('/').replace('ws://', 'http://').replace('wss://', 'https://')
        self.database = database
        if not self.uri or not database or not token:
            raise DatabaseError('SpacetimeDB is not configured. Set SPACETIMEDB_URI, SPACETIMEDB_DATABASE and SPACETIMEDB_TOKEN.')
        self.client = client or httpx.Client(timeout=httpx.Timeout(30, connect=5),
            headers={'Authorization': f'Bearer {token}'}, limits=httpx.Limits(max_connections=30, max_keepalive_connections=10))

    def table(self, name: str):
        if name not in SCHEMA:
            raise DatabaseError(f'Unknown table: {name}', 400)
        return Query(self, name)

    def execute(self, payload: dict) -> QueryResult:
        # Serialized payload and request_id stay identical across transport retries.
        body = [json.dumps(payload, separators=(',', ':'), default=str)]
        url = f'{self.uri}/v1/database/{quote(self.database, safe="")}/call/execute_query'
        response = None
        for attempt in range(3):
            try:
                response = self.client.post(url, json=body)
                break
            except httpx.TransportError as exc:
                if attempt == 2:
                    raise DatabaseError('SpacetimeDB is unreachable; the request may be retried safely.') from exc
                time.sleep(0.15 * (attempt + 1))
        if not response.is_success:
            detail = response.text
            status = 409 if any(x in detail.lower() for x in ('unique', 'duplicate', 'foreign key')) else 503
            if response.status_code in (401, 403):
                detail = 'SpacetimeDB rejected the configured backend identity.'
            else:
                # Never expose credentials or raw rows from a remote error.
                detail = 'SpacetimeDB request failed: ' + detail[:250]
            raise DatabaseError(detail, status)
        try:
            result = response.json()
            if isinstance(result, dict) and 'Ok' in result:
                result = result['Ok']
            if isinstance(result, str):
                result = json.loads(result)
            if not isinstance(result, dict) or not isinstance(result.get('data'), list):
                raise ValueError('Unexpected response')
            return QueryResult(result['data'], result.get('count', len(result['data'])))
        except (ValueError, TypeError) as exc:
            raise DatabaseError('Invalid response from SpacetimeDB') from exc


class Query:
    def __init__(self, db, table):
        self.db = db
        self.payload = {'table': table, 'operation': 'select', 'filters': [], 'orders': []}
        self.negate_next = False

    def _field(self, field):
        if field not in SCHEMA[self.payload['table']]:
            raise DatabaseError(f'Unknown field: {field}', 400)
        return field

    def select(self, fields='*', **kwargs):
        self.payload['fields'] = [] if fields == '*' else [self._field(f.strip()) for f in fields.split(',')]
        return self

    def _filter(self, field, op, value):
        self.payload['filters'].append({'field': self._field(field), 'op': op, 'value': value, 'negate': self.negate_next})
        self.negate_next = False
        return self

    def eq(self, f, v): return self._filter(f, 'eq', v)
    def neq(self, f, v): return self._filter(f, 'neq', v)
    def gte(self, f, v): return self._filter(f, 'gte', v)
    def lte(self, f, v): return self._filter(f, 'lte', v)
    def gt(self, f, v): return self._filter(f, 'gt', v)
    def lt(self, f, v): return self._filter(f, 'lt', v)
    def in_(self, f, v): return self._filter(f, 'in', v)
    def ilike(self, f, v): return self._filter(f, 'ilike', v)
    def is_(self, f, v): return self._filter(f, 'is', v)

    @property
    def not_(self):
        self.negate_next = True
        return self

    def or_(self, expression):
        filters = []
        for clause in expression.split(','):
            field, op, value = clause.split('.', 2)
            if op != 'ilike':
                raise DatabaseError('Unsupported OR operator', 400)
            filters.append({'field': self._field(field), 'op': op, 'value': value})
        self.payload['any'] = filters
        return self

    def order(self, field, desc=False):
        self.payload['orders'].append({'field': self._field(field), 'desc': bool(desc)})
        return self

    def limit(self, n):
        self.payload['limit'] = max(0, int(n))
        return self

    def range(self, start, end):
        self.payload['offset'] = max(0, int(start))
        return self.limit(int(end) - int(start) + 1)

    def _write(self, op, data=None):
        self.payload.update(operation=op, request_id=str(uuid4()))
        if data is not None:
            data = deepcopy(data)
            if op in ('insert', 'upsert'):
                for row in data if isinstance(data, list) else [data]:
                    row.setdefault('id', str(uuid4()))
            self.payload['data'] = data
        return self

    def insert(self, data): return self._write('insert', data)
    def upsert(self, data): return self._write('upsert', data)
    def update(self, data): return self._write('update', data)
    def increment(self, data): return self._write('increment', data)
    def delete(self): return self._write('delete')
    def execute(self): return self.db.execute(self.payload)


@lru_cache
def get_database() -> SpacetimeDatabase:
    settings = get_settings()
    return SpacetimeDatabase(settings.spacetimedb_uri, settings.spacetimedb_database, settings.spacetimedb_token)
