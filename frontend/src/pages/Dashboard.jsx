/**
 * City-level missing persons dashboard — aggregate patterns only.
 */
import { useEffect, useState } from 'react'
import { getCityDashboard, getCrossCasePatterns } from '../advancedApi.js'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [patterns, setPatterns] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getCityDashboard(), getCrossCasePatterns(2)])
      .then(([s, p]) => {
        setStats(s)
        setPatterns(p)
      })
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="page-pad space-y-8 pt-10">
      <div>
        <p
          className="text-[11px] font-semibold uppercase text-accent"
          style={{ letterSpacing: '3px' }}
        >
          Public data
        </p>
        <h1 className="mt-2 font-display text-3xl text-navy sm:text-4xl">
          City activity dashboard
        </h1>
        <p className="mt-2 max-w-2xl text-text-muted">
          Aggregate patterns only — no personal tip content. Useful for awareness, not investigation
          certainty.
        </p>
      </div>

      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {stats && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Active cases', stats.active_cases],
            ['Found / resolved', stats.found_cases],
            ['Resolved this month', stats.resolved_this_month],
            [
              'All-time resolution rate',
              `${Math.round((stats.resolution_rate_all_time || 0) * 100)}%`,
            ],
          ].map(([label, value]) => (
            <div key={label} className="surface-card p-4">
              <p className="text-[11px] font-bold uppercase tracking-wide text-text-muted">
                {label}
              </p>
              <p className="mt-2 font-display text-3xl text-navy">{value}</p>
            </div>
          ))}
        </section>
      )}

      {stats?.top_last_seen_areas && (
        <section className="surface-card p-5">
          <h2 className="font-display text-2xl text-navy">Most common last-seen areas</h2>
          <ul className="mt-4 space-y-2">
            {stats.top_last_seen_areas.map((a) => (
              <li
                key={a.area}
                className="flex items-center justify-between border-b border-border py-2 text-sm"
              >
                <span>{a.area}</span>
                <span className="font-semibold text-navy">{a.count}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {patterns && (
        <section className="surface-card p-5">
          <h2 className="font-display text-2xl text-navy">Cross-case geographic patterns</h2>
          <p className="mt-1 text-xs text-text-muted">
            Provenance: {patterns.provenance}. {patterns.note}
          </p>
          {(patterns.clusters || []).length === 0 ? (
            <p className="mt-3 text-sm text-text-muted">No multi-case tip clusters detected yet.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {patterns.clusters.map((c, i) => (
                <li key={i} className="rounded-lg border border-border bg-cream p-3 text-sm">
                  <p className="font-semibold text-navy">{c.summary}</p>
                  <p className="mt-1 text-text-muted">
                    Cases: {c.cases.map((x) => x.name).join(', ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
