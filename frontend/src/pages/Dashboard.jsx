/**
 * City-level missing persons dashboard — aggregate patterns + civic context.
 */
import { useEffect, useState } from 'react'
import { getCityDashboard, getCrossCasePatterns, getBaltimoreCivic } from '../advancedApi.js'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [patterns, setPatterns] = useState(null)
  const [civic, setCivic] = useState(null)
  const [error, setError] = useState('')
  const [showNotebook, setShowNotebook] = useState(false)

  useEffect(() => {
    Promise.all([
      getCityDashboard(),
      getCrossCasePatterns(2),
      getBaltimoreCivic().catch(() => null),
    ])
      .then(([s, p, c]) => {
        setStats(s)
        setPatterns(p)
        setCivic(c)
      })
      .catch((err) => setError(err.message))
  }, [])

  const ratePct = Math.round((stats?.resolution_rate_all_time || 0) * 100)

  return (
    <div className="page-pad space-y-8 pt-10">
      <div>
        <p className="section-label">Public data</p>
        <h1 className="mt-2 font-display text-3xl text-ink sm:text-4xl">
          City activity dashboard
        </h1>
        <p className="mt-2 max-w-2xl text-text-muted">
          Aggregate patterns only — no personal tip content. Useful for awareness, not
          investigation certainty.
        </p>
      </div>

      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {stats ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Active cases', stats.active_cases ?? 0],
            ['Found / resolved', stats.found_cases ?? 0],
            ['Resolved this month', stats.resolved_this_month ?? 0],
            ['All-time resolution rate', `${ratePct}%`],
          ].map(([label, value]) => (
            <div key={label} className="surface-card p-4">
              <p className="text-[11px] font-bold uppercase tracking-wide text-text-muted">
                {label}
              </p>
              <p className="mt-2 font-display text-3xl text-ink">{value}</p>
            </div>
          ))}
        </section>
      ) : (
        !error && (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="surface-card h-24 animate-pulse bg-misty/40" />
            ))}
          </section>
        )
      )}

      {stats?.top_last_seen_areas?.length > 0 && (
        <section className="surface-card p-5">
          <h2 className="font-display text-2xl text-ink">Most common last-seen areas</h2>
          <p className="mt-1 text-xs text-text-muted">Active cases only</p>
          <ul className="mt-4 space-y-2">
            {stats.top_last_seen_areas.map((a) => (
              <li
                key={a.area}
                className="flex items-center justify-between border-b border-border py-2 text-sm"
              >
                <span>{a.area}</span>
                <span className="font-semibold text-ink">{a.count}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {patterns && (
        <section className="surface-card p-5">
          <h2 className="font-display text-2xl text-ink">Cross-case geographic patterns</h2>
          <p className="mt-1 text-xs text-text-muted">
            Provenance: {patterns.provenance}. {patterns.note}
          </p>
          {(patterns.clusters || []).length === 0 ? (
            <p className="mt-3 text-sm text-text-muted">No multi-case tip clusters detected yet.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {patterns.clusters.map((c, i) => (
                <li key={i} className="rounded-lg border border-border bg-cream p-3 text-sm">
                  <p className="font-semibold text-ink">{c.summary}</p>
                  <p className="mt-1 text-text-muted">
                    Cases: {c.cases.map((x) => x.name).join(', ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {civic && (
        <section className="surface-card border-l-4 border-l-sage p-5 sm:p-6">
          <p className="section-label">Marimo · Baltimore open data</p>
          <h2 className="mt-1 font-display text-2xl text-ink">{civic.title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-text-muted">{civic.story}</p>
          <p className="mt-2 text-xs text-text-muted">{civic.disclaimer}</p>
          <p className="mt-3 text-sm text-ink">
            Tip density is for <strong>active</strong> cases only. Found cases are excluded.
            On an active case page → Tips &amp; Map: nearest listed CitiWatch cameras by distance
            (no live video).
          </p>
          {civic.open_data?.portal ? (
            <p className="mt-2 text-xs">
              <a
                href={civic.open_data.portal}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-sage underline"
              >
                CitiWatch on Open Data
              </a>
            </p>
          ) : null}
          <button
            type="button"
            className="btn-secondary mt-4"
            onClick={() => setShowNotebook((v) => !v)}
          >
            {showNotebook ? 'Hide notebook steps' : 'Run interactive notebook'}
          </button>
          {showNotebook && (
            <div className="mt-3 rounded-lg bg-cream px-4 py-3 text-left text-sm text-ink">
              <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-text-muted">
                {`cd backend
.venv\\Scripts\\activate
pip install marimo pandas folium httpx
marimo run ..\\notebooks\\baltimore_civic_story.py`}
              </pre>
              <p className="mt-2 text-xs text-text-muted">
                Notebook: <code className="rounded bg-stone px-1">{civic.marimo_notebook}</code>
              </p>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
