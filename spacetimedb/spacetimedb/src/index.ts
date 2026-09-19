/** Native SpacetimeDB storage. Only the publishing backend identity can access private case data. */
import { schema, table, t, SenderError } from 'spacetimedb/server';
import { appTables } from './tables';
import { specs } from './spec';

const backend_access = table({ name: 'backend_access' }, { id: t.string().primaryKey(), identity: t.identity() });
const write_receipts = table({ name: 'write_receipts' }, {
  id: t.string().primaryKey(), fingerprint: t.string(), result: t.string(), created_at: t.string(),
});
// Deliberately excludes tip text, coordinates, owner tokens, and submitter emails.
const case_activity = table({ name: 'case_activity', public: true }, {
  id: t.string().primaryKey(), person_id: t.string().index('btree'), person_name: t.string(),
  kind: t.string(), created_at: t.string(),
});
const spacetimedb = schema({ ...appTables, backend_access, write_receipts, case_activity });
export default spacetimedb;

export const init = spacetimedb.init(ctx => {
  ctx.db.backend_access.insert({ id: 'backend', identity: ctx.sender });
});

type Row = Record<string, any>;
type Filter = { field: string; op: string; value: any; negate?: boolean };
type Query = { table: string; operation: string; fields?: string[]; filters?: Filter[];
  any?: Filter[]; orders?: { field: string; desc: boolean }[]; limit?: number; offset?: number;
  data?: Row | Row[]; request_id?: string };
const definitions: Record<string, Record<string, any>> = specs;
const fail = (message: string): never => { throw new SenderError(message); };

function column(tableName: string, field: string) {
  if (!Object.prototype.hasOwnProperty.call(definitions[tableName], field)) fail(`Unknown field ${field}`);
}
function matches(row: Row, filter: Filter): boolean {
  const a = row[filter.field] ?? null, b = filter.value;
  let result: boolean;
  switch (filter.op) {
    case 'eq': result = a !== null && a === b; break;
    case 'neq': result = a !== null && a !== b; break;
    case 'gte': result = a !== null && a >= b; break;
    case 'lte': result = a !== null && a <= b; break;
    case 'gt': result = a !== null && a > b; break;
    case 'lt': result = a !== null && a < b; break;
    case 'in': result = a !== null && Array.isArray(b) && b.includes(a); break;
    case 'is': result = a === (b === 'null' ? null : b); break;
    case 'ilike': {
      let pattern = '', escaped = false;
      for (const ch of String(b)) {
        if (!escaped && ch === '\\') { escaped = true; continue; }
        pattern += !escaped && (ch === '%' || ch === '*') ? '.*' : !escaped && ch === '_' ? '.' : ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        escaped = false;
      }
      if (escaped) pattern += '\\\\';
      result = a !== null && new RegExp(`^${pattern}$`, 'isu').test(String(a));
      break;
    }
    default: return fail('Unsupported filter');
  }
  return filter.negate ? !result : result;
}
function decode(tableName: string, row: Row): Row {
  return Object.fromEntries(Object.entries(definitions[tableName]).map(([key, spec]) => [key,
    row[key] === undefined ? null : spec.type === 'json' ? JSON.parse(row[key]) : row[key]]));
}
function normalize(tableName: string, row: Row, now: string): Row {
  const out: Row = {};
  for (const key of Object.keys(row)) column(tableName, key);
  for (const [key, spec] of Object.entries(definitions[tableName])) {
    let value = row[key];
    if (value === undefined && spec.default !== undefined) {
      value = spec.default === 'now' ? now : spec.default === 'uuid' ? undefined : spec.default;
    }
    if (value === undefined || value === null) {
      if (!spec.nullable) fail(`${tableName}.${key} is required`);
      out[key] = undefined;
      continue;
    }
    if (spec.type === 'json') value = JSON.stringify(value);
    else if (spec.type === 'string' && typeof value !== 'string') fail(`${key} must be a string`);
    else if (spec.type === 'boolean' && typeof value !== 'boolean') fail(`${key} must be boolean`);
    else if (['number', 'integer'].includes(spec.type) && (typeof value !== 'number' || !Number.isFinite(value) || (spec.type === 'integer' && !Number.isInteger(value)))) fail(`${key} must be numeric`);
    if (spec.sql_type === 'UUID' && !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) fail(`Invalid UUID for ${key}`);
    if (spec.sql_type === 'TIMESTAMPTZ') {
      if (!Number.isFinite(Date.parse(value))) fail(`Invalid timestamp for ${key}`);
      // Preserve source microsecond precision; JS Date would truncate it.
    }
    if (spec.sql_type === 'DATE' && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value)))) fail(`Invalid date for ${key}`);
    out[key] = value;
  }
  const range = (key: string, min: number, max: number) => {
    if (out[key] != null && (out[key] < min || out[key] > max)) fail(`Out of range: ${key}`);
  };
  range('age', 0, 150); range('location_lat', -90, 90); range('location_lng', -180, 180);
  range('confidence_level', 1, 5); range('credibility_score', 1, 10);
  const allowed: Record<string, Record<string, string[]>> = {
    persons: { status: ['active', 'found', 'closed'] }, users: { role: ['family', 'public'] },
    case_coordinators: { role: ['coordinator', 'owner'] },
    alert_subscriptions: { kind: ['natural_language', 'zip', 'case_watch'] },
    case_source_links: { source_type: ['agency_listing', 'news_article', 'public_appeal', 'other'] },
  };
  for (const [key, values] of Object.entries(allowed[tableName] || {})) if (!values.includes(out[key])) fail(`Invalid ${key}`);
  return out;
}
function constraints(ctx: any, tableName: string, row: Row) {
  if (row.person_id && !ctx.db.persons.id.find(row.person_id)) fail('Foreign key: person not found');
  const uniques: Record<string, string[][]> = {
    users: [['email']], case_coordinators: [['person_id', 'email']],
    search_memory: [['participant_key']], case_source_links: [['person_id', 'url']],
  };
  for (const fields of uniques[tableName] || []) {
    for (const other of ctx.db[tableName].iter()) {
      if (other.id !== row.id && fields.every(key => other[key] === row[key])) fail('Unique constraint violated');
    }
  }
  if (tableName === 'alert_subscriptions' && row.kind === 'case_watch' && row.active && row.person_id) {
    for (const other of ctx.db.alert_subscriptions.person_id.filter(row.person_id)) {
      if (other.id !== row.id && other.active && other.kind === 'case_watch' && other.email.toLowerCase() === row.email.toLowerCase()) fail('Duplicate active case watcher');
    }
  }
}
function refreshCounts(ctx: any, personId: string) {
  const person = ctx.db.persons.id.find(personId);
  if (!person) return;
  const tips = [...ctx.db.sightings.person_id.filter(personId)].length;
  const watchers = [...ctx.db.alert_subscriptions.person_id.filter(personId)].filter((r: any) => r.active && r.kind === 'case_watch').length;
  ctx.db.persons.id.update({ ...person, tips_count: tips, watchers_count: watchers });
}
function removeRow(ctx: any, tableName: string, row: Row) {
  if (tableName === 'persons') {
    for (const child of Object.keys(definitions).filter(name => name !== 'persons' && definitions[name].person_id)) {
      for (const entry of [...ctx.db[child].person_id.filter(row.id)]) {
        if (child === 'live_tip_events') ctx.db[child].id.update({ ...entry, person_id: undefined });
        else ctx.db[child].id.delete(entry.id);
      }
    }
    for (const event of [...ctx.db.case_activity.person_id.filter(row.id)]) ctx.db.case_activity.id.delete(event.id);
  }
  ctx.db[tableName].id.delete(row.id);
}

// A procedure is used to return the exact committed rows to FastAPI in one call.
// All reads/updates and constraints execute inside one SpacetimeDB transaction.
export const execute_query = spacetimedb.procedure({ request: t.string() }, t.string(), (ctx, { request }) => {
  const q: Query = JSON.parse(request);
  return ctx.withTx(tx => {
    const access = tx.db.backend_access.id.find('backend');
    if (!access || !ctx.sender.isEqual(access.identity)) fail('Unauthorized backend identity');
    if (!Object.prototype.hasOwnProperty.call(definitions, q.table)) fail('Unknown table');
    const db: any = tx.db, target = db[q.table];
    const op = q.operation;
    if (!['select', 'insert', 'update', 'delete', 'upsert', 'increment'].includes(op)) fail('Unsupported operation');
    const filters = q.filters || [], any = q.any || [];
    for (const filter of [...filters, ...any]) column(q.table, filter.field);
    for (const field of q.fields || []) column(q.table, field);
    for (const order of q.orders || []) column(q.table, order.field);
    const writing = op !== 'select';
    if (writing && !q.request_id) fail('Write request ID is required');
    if (writing) {
      const receipt = tx.db.write_receipts.id.find(q.request_id!);
      if (receipt) {
        if (receipt.fingerprint !== request) fail('Request ID reused with different data');
        return receipt.result;
      }
    }
    const now = tx.timestamp.toDate().toISOString();
    const getRows = (): Row[] => {
      const byId = filters.find(f => f.field === 'id' && f.op === 'eq' && !f.negate);
      const byParent = filters.find(f => f.field === 'person_id' && f.op === 'eq' && !f.negate);
      const source = byId ? [target.id.find(byId.value)].filter(Boolean) : byParent && target.person_id ? [...target.person_id.filter(byParent.value)] : [...target.iter()];
      return source.map((r: Row) => decode(q.table, r)).filter((r: Row) => filters.every(f => matches(r, f)) && (!any.length || any.some(f => matches(r, f))));
    };
    let output: Row[] = [];
    if (op === 'select') {
      output = getRows();
      const orders = [...(q.orders || []), { field: 'id', desc: false }];
      output.sort((a, b) => {
        for (const order of orders) {
          const x = a[order.field], y = b[order.field];
          if (x === y) continue;
          if (x == null) return order.desc ? -1 : 1;
          if (y == null) return order.desc ? 1 : -1;
          return (x < y ? -1 : 1) * (order.desc ? -1 : 1);
        }
        return 0;
      });
      const count = output.length;
      output = output.slice(q.offset || 0, q.limit === undefined ? undefined : (q.offset || 0) + q.limit);
      if (q.fields?.length) output = output.map(row => Object.fromEntries(q.fields!.map(k => [k, row[k]])));
      return JSON.stringify({ data: output, count });
    }
    if (op === 'insert' || op === 'upsert') {
      const rows = Array.isArray(q.data) ? q.data : [q.data];
      for (const raw of rows) {
        if (!raw) fail('Missing insert data');
        const row = normalize(q.table, raw!, now);
        constraints(tx, q.table, row);
        if (op === 'upsert' && target.id.find(row.id)) target.id.update(row); else target.insert(row);
        output.push(decode(q.table, row));
      }
    } else {
      if (!filters.length) fail('A write filter is required');
      for (const old of getRows()) {
        if (op === 'delete') { removeRow(tx, q.table, old); output.push(old); continue; }
        const changes = { ...q.data } as Row;
        if (changes.id !== undefined && changes.id !== old.id) fail('Primary keys are immutable');
        if (op === 'increment') for (const key of Object.keys(changes)) changes[key] = Number(old[key] || 0) + Number(changes[key]);
        const row = normalize(q.table, { ...old, ...changes }, now);
        constraints(tx, q.table, row);
        target.id.update(row);
        output.push(decode(q.table, row));
      }
    }
    for (const row of output) {
      if (row.person_id && ['sightings', 'alert_subscriptions'].includes(q.table)) refreshCounts(tx, row.person_id);
      if (q.table === 'persons' && op !== 'delete') refreshCounts(tx, row.id);
      if (q.table === 'sightings' && ['insert', 'upsert'].includes(op)) {
        const person = db.persons.id.find(row.person_id);
        if (!tx.db.case_activity.id.find(row.id)) tx.db.case_activity.insert({ id: row.id, person_id: row.person_id, person_name: person?.name || 'Case', kind: 'tip_submitted', created_at: row.created_at });
      }
      if (q.table === 'sightings' && op === 'delete') tx.db.case_activity.id.delete(row.id);
    }
    if (q.table === 'persons' && op !== 'delete') output = output.map(r => decode('persons', db.persons.id.find(r.id)));
    const result = JSON.stringify({ data: output, count: output.length });
    // Receipts make retries safe after an uncertain network response.
    tx.db.write_receipts.insert({ id: q.request_id!, fingerprint: request, result, created_at: now });
    let removed = 0;
    for (const receipt of tx.db.write_receipts.iter()) {
      if (receipt.created_at < new Date(Date.parse(now) - 86400000).toISOString()) { tx.db.write_receipts.id.delete(receipt.id); if (++removed >= 100) break; }
    }
    return result;
  });
});
