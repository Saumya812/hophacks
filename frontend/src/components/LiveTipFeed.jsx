/**
 * Live tip feed — polls /live/tips (SpacetimeDB stand-in).
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getLiveTips } from '../advancedApi.js'

export default function LiveTipFeed() {
  const [tips, setTips] = useState([])
  const [note, setNote] = useState('')

  useEffect(() => {
    let alive = true
    async function tick() {
      try {
        const data = await getLiveTips(10)
        if (!alive) return
        setTips(data.tips || [])
        setNote(data.note || '')
      } catch {
        if (alive) setNote('Live feed unavailable')
      }
    }
    tick()
    const id = setInterval(tick, 4000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return (
    <aside className="surface-panel flex flex-col">
      <div className="border-b border-navy/10 bg-navy px-4 py-3 text-white">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/50">Live</p>
        <h2 className="font-display text-xl">Recent tips</h2>
      </div>
      <ul className="max-h-80 flex-1 space-y-0 overflow-y-auto">
        {tips.length === 0 && (
          <li className="px-4 py-6 text-sm text-navy/50">No tips yet — submit one to see the feed move.</li>
        )}
        {tips.map((t) => (
          <li key={t.id || `${t.person_id}-${t.created_at}`} className="border-b border-navy/10 px-4 py-3">
            <p className="text-xs text-navy/45">
              {t.created_at ? new Date(t.created_at).toLocaleTimeString() : ''}
            </p>
            <Link to={`/person/${t.person_id}`} className="font-semibold text-navy hover:underline">
              {t.person_name || 'Case'}
            </Link>
            <p className="mt-1 line-clamp-2 text-sm text-navy/75">{t.snippet}</p>
          </li>
        ))}
      </ul>
      <p className="border-t border-navy/10 px-4 py-2 text-[11px] text-navy/45">{note}</p>
    </aside>
  )
}
