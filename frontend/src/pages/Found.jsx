/**
 * /found — resolved / reunited cases (status = found).
 * Uses existing listPersons API — no direct Supabase client.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPersons } from '../api.js'
import { formatEventDate } from '../lib/caseHelpers.js'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'month', label: 'This Month' },
  { id: 'year', label: 'This Year' },
  { id: 'children', label: 'Children' },
  { id: 'adults', label: 'Adults' },
]

function inThisMonth(iso) {
  if (!iso) return false
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
}

function inThisYear(iso) {
  if (!iso) return false
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  return d.getFullYear() === new Date().getFullYear()
}

function foundDate(p) {
  return p.found_at || p.last_verified_at || p.created_at || null
}

export default function Found() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await listPersons({ status: 'found' })
        if (cancelled) return
        setPersons(data.persons || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load found cases')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const yearCount = useMemo(
    () => persons.filter((p) => inThisYear(foundDate(p))).length,
    [persons],
  )

  const filtered = useMemo(() => {
    return persons.filter((p) => {
      const fd = foundDate(p)
      if (filter === 'month') return inThisMonth(fd)
      if (filter === 'year') return inThisYear(fd)
      if (filter === 'children') return Number(p.age) < 18
      if (filter === 'adults') return Number(p.age) >= 18
      return true
    })
  }, [persons, filter])

  return (
    <div className="bg-cream pb-16">
      <section className="border-b border-border bg-stone/40 py-[60px] text-center">
        <div className="mx-auto max-w-[800px] px-4">
          <p
            className="text-[11px] font-medium uppercase text-sage"
            style={{ letterSpacing: '3px' }}
          >
            Resolved Cases
          </p>
          <h1 className="mt-3 font-display text-4xl font-normal text-ink sm:text-5xl">
            Found &amp; Reunited
          </h1>
          <p className="mt-4 text-base text-text-muted">
            These individuals were reported missing and have since been found safe.
          </p>
          <p className="mt-6 font-display text-2xl italic text-sage">
            {loading ? '…' : `${yearCount} people reunited this year`}
          </p>
        </div>
      </section>

      <div className="sticky top-16 z-30 border-b border-border bg-cream/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1200px] flex-wrap gap-2 px-4 py-3 sm:px-6">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
                filter === f.id
                  ? 'bg-navy text-white'
                  : 'border border-navy bg-white text-navy hover:bg-misty/40'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

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
        ) : filtered.length === 0 ? (
          <div className="px-4 py-20 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center text-navy">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
                <path
                  d="M7 12.5l3 3 7-7"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h3 className="font-display text-2xl text-navy">No resolved cases yet</h3>
            <p className="mx-auto mt-2 max-w-md text-base text-text-muted">
              When missing persons are found and marked safe, they will appear here.
            </p>
          </div>
        ) : (
          <div
            className="grid gap-6"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
          >
            {filtered.map((p) => {
              const fd = foundDate(p)
              return (
                <article
                  key={p.id}
                  className="card-interactive overflow-hidden"
                >
                  <div className="relative h-60 overflow-hidden bg-misty/40">
                    {p.photo_url ? (
                      <img
                        src={p.photo_url}
                        alt={p.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center font-display text-5xl text-navy/25">
                        {(p.name || '?').charAt(0)}
                      </div>
                    )}
                    <div
                      className="absolute inset-x-0 bottom-0 px-4 py-3"
                      style={{
                        background: 'linear-gradient(transparent, rgba(22,163,74,0.9))',
                      }}
                    >
                      <p
                        className="text-[11px] font-semibold uppercase text-white"
                        style={{ letterSpacing: '2px' }}
                      >
                        Found safe
                      </p>
                    </div>
                  </div>
                  <div className="p-5">
                    <h2 className="font-display text-[22px] text-navy">{p.name}</h2>
                    <p className="mt-1 text-[13px] text-text-muted">
                      Age {p.age}
                      {p.gender ? ` · ${p.gender}` : ''}
                    </p>
                    <dl className="mt-4 space-y-1.5 text-[13px]">
                      <div className="flex justify-between gap-2">
                        <dt className="text-text-muted">Missing since:</dt>
                        <dd className="text-navy">
                          {formatEventDate(p.last_seen_date) || p.last_seen_date || 'Unknown'}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-2">
                        <dt className="text-text-muted">Found on:</dt>
                        <dd className="text-success">
                          {formatEventDate(fd) || formatEventDate(String(fd || '').slice(0, 10)) || 'Unknown'}
                        </dd>
                      </div>
                    </dl>
                    {p.description && (
                      <>
                        <div className="my-3 h-px bg-border" />
                        <p className="line-clamp-3 text-[13px] text-text-muted">{p.description}</p>
                      </>
                    )}
                    <div className="mt-4 flex items-center justify-between gap-2">
                      <span className="truncate rounded-full bg-misty px-3 py-1 text-xs text-navy">
                        {p.last_seen_location || 'Location on file'}
                      </span>
                      <Link
                        to={`/person/${p.id}`}
                        className="shrink-0 text-[13px] font-semibold text-gold hover:underline"
                      >
                        View details →
                      </Link>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
