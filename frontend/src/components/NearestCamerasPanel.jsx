/**
 * Nearest listed CitiWatch cameras for a case (distance-based, not live video).
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getBaltimoreNearest } from '../advancedApi.js'
import { formatEventDateTime } from '../lib/caseHelpers.js'

export default function NearestCamerasPanel({ personId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getBaltimoreNearest(personId)
      .then((d) => {
        if (!cancelled) setData(d)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Could not load camera listings')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [personId])

  if (loading) {
    return (
      <section className="surface-card p-5">
        <p className="section-label">CitiWatch listings</p>
        <p className="mt-2 text-sm text-text-muted">Finding nearest listed cameras…</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="surface-card p-5">
        <p className="section-label">CitiWatch listings</p>
        <p className="mt-2 text-sm text-amber-900">{error}</p>
        <p className="mt-2 text-xs text-text-muted">
          Camera suggestions need Baltimore GIS. Tips and face match still work without this panel.
        </p>
      </section>
    )
  }

  if (!data) return null

  const tips = data.tips || []
  const lastSeen = data.last_seen

  return (
    <section className="surface-card border-l-4 border-l-sage p-5 sm:p-6">
      <p className="section-label">Public camera listings · not live video</p>
      <h2 className="mt-1 font-display text-2xl text-ink">Nearest CitiWatch cameras</h2>
      <p className="mt-2 text-sm leading-relaxed text-text-muted">{data.disclaimer}</p>

      <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm text-ink">
        {(data.how_to_use || []).map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>

      <p className="mt-3 text-xs text-text-muted">{data.face_match_note}</p>

      {lastSeen && (
        <div className="mt-5 rounded-lg border border-border bg-cream p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Near reported last-seen
          </p>
          <p className="mt-1 text-sm text-ink">{lastSeen.query}</p>
          {lastSeen.note && (
            <p className="mt-1 text-xs text-text-muted">{lastSeen.note}</p>
          )}
          <CameraList cameras={lastSeen.nearest_cameras} />
        </div>
      )}

      <div className="mt-5 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Per community tip ({data.tips_with_cameras || 0} with nearby listings)
        </p>
        {tips.length === 0 ? (
          <p className="text-sm text-text-muted">
            No geocoded tips yet. When tips arrive, nearest listed cameras show here.
          </p>
        ) : (
          tips.map((t) => (
            <div key={t.tip_id} className="rounded-lg border border-border bg-white p-4">
              <p className="text-xs text-text-muted">
                Tip · {formatEventDateTime(t.date_time) || 'Unknown date'}
              </p>
              <p className="mt-1 line-clamp-2 text-sm text-ink">{t.snippet || 'Community tip'}</p>
              <CameraList cameras={t.nearest_cameras} />
            </div>
          ))
        )}
      </div>

      <p className="mt-4 text-xs text-text-muted">
        Full city map:{' '}
        <Link to="/dashboard" className="font-medium text-sage underline">
          Dashboard → Baltimore civic context
        </Link>{' '}
        (marimo). Catalog size: {data.camera_catalog_count} listings loaded.
      </p>
    </section>
  )
}

function CameraList({ cameras }) {
  if (!cameras?.length) {
    return (
      <p className="mt-2 text-xs text-text-muted">
        No listed CitiWatch cameras within range of this point.
      </p>
    )
  }
  return (
    <ul className="mt-2 space-y-1.5">
      {cameras.map((c) => (
        <li
          key={`${c.cam_number}-${c.lat}-${c.lng}`}
          className="flex flex-wrap items-baseline justify-between gap-2 text-sm"
        >
          <span className="text-ink">
            <span className="font-medium">#{c.cam_number}</span> · {c.location}
          </span>
          <span className="shrink-0 text-xs font-medium text-sage">{c.distance_label}</span>
        </li>
      ))}
      <li className="pt-1 text-[11px] text-text-muted">
        Suggested ask (official channels only): “Please review CitiWatch listings near{' '}
        {cameras[0].location}.”
      </li>
    </ul>
  )
}
