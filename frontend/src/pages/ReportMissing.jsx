/**
 * /report-missing — browse active cases (form stays at /report).
 * Matches Found / cream-page layout (no navy hero).
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPersons } from '../api.js'
import { formatEventDate } from '../lib/caseHelpers.js'

export default function ReportMissing() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await listPersons({ status: 'active' })
        if (cancelled) return
        const list = [...(data.persons || [])].sort((a, b) => {
          const ta = new Date(a.created_at || 0).getTime()
          const tb = new Date(b.created_at || 0).getTime()
          return tb - ta
        })
        setPersons(list)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load cases')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="bg-cream pb-16">
      <section className="border-b border-border bg-stone/40 py-[60px] text-center">
        <div className="mx-auto max-w-[800px] px-4">
          <p
            className="text-[11px] font-medium uppercase text-sage"
            style={{ letterSpacing: '3px' }}
          >
            Active Cases
          </p>
          <h1 className="mt-3 font-display text-4xl font-normal text-ink sm:text-5xl">
            Missing Persons
          </h1>
          <p className="mt-4 text-base text-text-muted">
            Click any case to view updates and submit a tip.
          </p>
          <p className="mt-6 font-display text-2xl italic text-sage">
            {loading ? '…' : `${persons.length} active ${persons.length === 1 ? 'case' : 'cases'}`}
          </p>
          <p className="mt-4 text-sm text-text-muted">
            Need to file a new case?{' '}
            <Link to="/report" className="font-semibold text-ink underline decoration-sage/60 underline-offset-2 hover:text-sage">
              Report
            </Link>
          </p>
        </div>
      </section>

      <div className="mx-auto max-w-[1200px] px-6 py-[60px]">
        {error && (
          <p className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </p>
        )}

        {loading ? (
          <div
            className="grid gap-6"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="surface-card h-80 animate-pulse bg-misty/40" />
            ))}
          </div>
        ) : persons.length === 0 ? (
          <div className="px-4 py-20 text-center">
            <h3 className="font-display text-2xl text-ink">No active cases yet</h3>
            <p className="mx-auto mt-2 max-w-md text-base text-text-muted">
              When someone is reported missing, they will appear here.{' '}
              <Link to="/report" className="font-semibold text-ink underline">
                Report
              </Link>
            </p>
          </div>
        ) : (
          <div
            className="grid gap-6"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
          >
            {persons.map((p) => (
              <Link
                key={p.id}
                to={`/person/${p.id}`}
                className="card-interactive group overflow-hidden"
              >
                <div className="relative h-60 overflow-hidden bg-misty/40">
                  {p.photo_url ? (
                    <img
                      src={p.photo_url}
                      alt={p.name}
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center font-display text-5xl text-ink/20">
                      {(p.name || '?').charAt(0)}
                    </div>
                  )}
                  <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded bg-white/95 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-700 shadow-sm">
                    <span className="live-pulse-dot live-pulse-dot-alert" />
                    Active
                  </span>
                </div>
                <div className="p-5">
                  <h2 className="font-display text-[22px] text-ink group-hover:text-sage">
                    {p.name}
                  </h2>
                  <p className="mt-1 text-[13px] text-text-muted">
                    Age {p.age}
                    {p.gender ? ` · ${p.gender}` : ''}
                  </p>
                  <p className="mt-3 text-[13px] font-medium text-text-muted">
                    Last seen · {p.last_seen_location || 'Unknown'}
                    {p.last_seen_date
                      ? ` · ${formatEventDate(p.last_seen_date) || p.last_seen_date}`
                      : ''}
                  </p>
                  <span className="mt-4 inline-block text-sm font-semibold text-sage">
                    View case →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
