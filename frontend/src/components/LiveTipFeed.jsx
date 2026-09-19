/**
 * Live tip feed backed by a native SpacetimeDB subscription.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { DbConnection } from '../spacetime/index.ts'

export default function LiveTipFeed() {
  const [tips, setTips] = useState([])
  const [note, setNote] = useState('')

  useEffect(() => {
    let alive = true
    let connection
    let retry
    function reconnect() {
      if (!alive || retry) return
      setNote('Connecting to live updates…')
      retry = setTimeout(() => { retry = null; connect() }, 4000)
    }
    function connect() {
      if (!alive) return
      setNote('Connecting to live updates…')
      connection = DbConnection.builder()
        .withUri(import.meta.env.VITE_SPACETIMEDB_URI || 'ws://127.0.0.1:3000')
        .withDatabaseName(import.meta.env.VITE_SPACETIMEDB_DATABASE || 'findmypal')
        .onConnect((conn) => {
          if (!alive) { conn.disconnect(); return }
          const refresh = () => {
            if (!alive) return
            const rows = [...conn.db.caseActivity.iter()]
              .filter((row) => (row.kind || '') === 'tip_submitted')
              .sort((a, b) => {
                const ca = a.createdAt || ''
                const cb = b.createdAt || ''
                return cb.localeCompare(ca) || String(a.id).localeCompare(String(b.id))
              })
              .slice(0, 10)
              .map((row) => ({
                id: row.id,
                person_id: row.personId,
                person_name: row.personName,
                created_at: row.createdAt,
                snippet: 'New community tip submitted',
              }))
            setTips(rows)
          }
          conn.db.caseActivity.onInsert(refresh)
          conn.db.caseActivity.onUpdate(refresh)
          conn.db.caseActivity.onDelete(refresh)
          conn.subscriptionBuilder().onApplied(() => {
            refresh()
            if (alive) setNote('Live updates connected')
          }).onError(() => { conn.disconnect(); reconnect() })
            .subscribe('SELECT * FROM case_activity')
        })
        .onConnectError(reconnect)
        .onDisconnect(reconnect)
        .build()
    }
    connect()
    return () => {
      alive = false
      clearTimeout(retry)
      connection?.disconnect()
    }
  }, [])

  return (
    <aside className="surface-card flex flex-col overflow-hidden">
      <div className="border-b border-border bg-navy px-4 py-3 text-white">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/50">
          <span className="pulse-dot mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-accent" />
          Live
        </p>
        <h2 className="font-display text-xl">Recent tips</h2>
      </div>
      <ul className="max-h-80 flex-1 space-y-0 overflow-y-auto">
        {tips.length === 0 && (
          <li className="px-4 py-6 text-sm text-text-muted">
            No tips yet — submit one to see the feed move.
          </li>
        )}
        {tips.map((t) => (
          <li
            key={t.id || `${t.person_id}-${t.created_at}`}
            className="border-b border-border px-4 py-3"
          >
            <p className="text-xs text-text-muted">
              {t.created_at ? new Date(t.created_at).toLocaleTimeString() : ''}
            </p>
            <Link to={`/person/${t.person_id}`} className="font-semibold text-navy hover:underline">
              {t.person_name || 'Case'}
            </Link>
            <p className="mt-1 line-clamp-2 text-sm text-text-muted">{t.snippet}</p>
          </li>
        ))}
      </ul>
      {note ? (
        <p className="border-t border-border px-4 py-2 text-[10px] text-text-muted">{note}</p>
      ) : null}
    </aside>
  )
}
