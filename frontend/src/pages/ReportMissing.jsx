/**
 * /report-missing — browse active cases (form stays at /report).
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
    <div className="bg-cream pb-20">
      <section className="w-full bg-navy text-white">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-14">
          <h1
            className="font-display font-normal text-white"
            style={{ fontSize: '42px', lineHeight: 1.15 }}
          >
            Missing Persons
          </h1>
          <p className="mt-3 max-w-xl text-sm text-white/75 sm:text-base">
            Click any case to view real-time updates and submit a tip
          </p>
          <p className="mt-4 text-xs text-white/50">
            Need to file a new case?{' '}
            <Link to="/report" className="font-semibold text-accent underline">
              Open the report form
            </Link>
          </p>
        </div>
      </section>

      <div className="page-pad pt-8">
        {loading && <p className="text-text-muted">Loading active cases…</p>}
        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}
        {!loading && !error && persons.length === 0 && (
          <p className="text-text-muted">
            No active cases yet.{' '}
            <Link to="/report" className="font-semibold text-navy underline">
              Report someone missing
            </Link>
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {persons.map((p, index) => (
            <Link
              key={p.id}
              to={`/person/${p.id}`}
              className="card-interactive group fade-up overflow-hidden p-0"
              style={{ animationDelay: `${Math.min(index, 10) * 50}ms` }}
            >
              <div className="relative aspect-[4/3] bg-navy/10">
                {p.photo_url ? (
                  <img
                    src={p.photo_url}
                    alt=""
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center font-display text-4xl text-navy/25">
                    {(p.name || '?').charAt(0)}
                  </div>
                )}
                <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded bg-white/95 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-success shadow-sm">
                  <span className="live-pulse-dot" />
                  Active
                </span>
              </div>
              <div className="p-4">
                <h2 className="font-display text-xl text-navy group-hover:text-accent">{p.name}</h2>
                <p className="mt-1 text-sm text-text-muted">Age {p.age}</p>
                <p className="mt-2 text-[13px] font-medium text-accent">
                  Last seen · {p.last_seen_location || 'Unknown'}
                  {p.last_seen_date
                    ? ` · ${formatEventDate(p.last_seen_date) || p.last_seen_date}`
                    : ''}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
