/**
 * SpacetimeDB live helpers — subscribe to public case_activity.
 * Private tip/person rows stay backend-only; we refetch via FastAPI.
 */
import { useEffect, useRef } from 'react'
import { DbConnection } from '../spacetime/index.ts'

const URI = () => import.meta.env.VITE_SPACETIMEDB_URI || 'ws://127.0.0.1:3000'
const DB = () => import.meta.env.VITE_SPACETIMEDB_DATABASE || 'findmypal'

/**
 * Subscribe to case_activity and invoke callbacks for tip / found events.
 * Falls back silently if Spacetime is unreachable (callers should still poll).
 */
export function useCaseActivityLive({
  personId,
  onTipForPerson,
  onPersonFound,
  onAnyFound,
} = {}) {
  const tipCb = useRef(onTipForPerson)
  const foundCb = useRef(onPersonFound)
  const anyFoundCb = useRef(onAnyFound)
  tipCb.current = onTipForPerson
  foundCb.current = onPersonFound
  anyFoundCb.current = onAnyFound

  useEffect(() => {
    let alive = true
    let connection
    let retry

    function reconnect() {
      if (!alive || retry) return
      retry = setTimeout(() => {
        retry = null
        connect()
      }, 4000)
    }

    function handleRow(row) {
      if (!row) return
      const pid = row.personId || row.person_id
      const kind = row.kind || ''
      if (kind === 'tip_submitted' && personId && pid === personId) {
        tipCb.current?.(row)
      }
      if (kind === 'verified_found') {
        if (personId && pid === personId) foundCb.current?.(row)
        anyFoundCb.current?.(row)
      }
    }

    function connect() {
      if (!alive) return
      try {
        connection = DbConnection.builder()
          .withUri(URI())
          .withDatabaseName(DB())
          .onConnect((conn) => {
            if (!alive) {
              conn.disconnect()
              return
            }
            const onInsert = (_ctx, row) => handleRow(row)
            conn.db.caseActivity.onInsert(onInsert)
            conn.subscriptionBuilder()
              .onApplied(() => {
                /* initial sync — profile still loads via API */
              })
              .onError(() => {
                conn.disconnect()
                reconnect()
              })
              .subscribe('SELECT * FROM case_activity')
          })
          .onConnectError(reconnect)
          .onDisconnect(reconnect)
          .build()
      } catch {
        reconnect()
      }
    }

    connect()
    return () => {
      alive = false
      clearTimeout(retry)
      connection?.disconnect()
    }
  }, [personId])
}
