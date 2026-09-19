/**
 * Homepage — slim disclaimer, navy hero, search, active cases, collapsed tools.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { listPersons, naturalSearch } from '../api.js'
import PersonCard from '../components/PersonCard.jsx'
import FaceMatchPanel from '../components/FaceMatchPanel.jsx'
import LiveTipFeed from '../components/LiveTipFeed.jsx'
import AlertsAndMemoryPanel from '../components/AlertsAndMemoryPanel.jsx'

const DISCLAIMER_KEY = 'fmp-disclaimer-dismissed'

export default function Home() {
  const location = useLocation()
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('keyword')
  const [filtersUsed, setFiltersUsed] = useState(null)
  const [moreTools, setMoreTools] = useState(false)
  const [disclaimerOpen, setDisclaimerOpen] = useState(() => {
    try {
      return localStorage.getItem(DISCLAIMER_KEY) !== '1'
    } catch {
      return true
    }
  })

  const loadActive = useCallback(async () => {
    setLoading(true)
    setError('')
    setFiltersUsed(null)
    setQuery('')
    try {
      const data = await listPersons({ status: 'active' })
      setPersons(data.persons || [])
    } catch (err) {
      setError(err.message || 'Failed to load cases')
      setPersons([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (location.pathname === '/') loadActive()
  }, [location.pathname, location.key, loadActive])

  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === 'visible' && location.pathname === '/') {
        loadActive()
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [location.pathname, loadActive])

  async function handleSearch(e) {
    e.preventDefault()
    const q = query.trim()
    if (!q) {
      loadActive()
      return
    }

    setLoading(true)
    setError('')
    setFiltersUsed(null)
    try {
      if (mode === 'natural') {
        const data = await naturalSearch(q)
        setPersons(data.persons || [])
        setFiltersUsed(data.filters || null)
      } else {
        let data = await listPersons({ name: q, status: 'active' })
        if (!data.count) {
          data = await listPersons({ location: q, status: 'active' })
        }
        setPersons(data.persons || [])
      }
    } catch (err) {
      setError(err.message || 'Search failed')
      setPersons([])
    } finally {
      setLoading(false)
    }
  }

  function dismissDisclaimer() {
    setDisclaimerOpen(false)
    try {
      localStorage.setItem(DISCLAIMER_KEY, '1')
    } catch {
      /* ignore */
    }
  }

  return (
    <div>
      {disclaimerOpen && (
        <aside
          role="note"
          className="flex h-9 items-center gap-3 border-b border-border bg-cream px-4 text-xs text-text-muted sm:px-6"
        >
          <p className="min-w-0 flex-1 truncate">
            Community tip platform — not affiliated with law enforcement. Call emergency services
            if someone is in immediate danger. Misuse may have legal consequences.
          </p>
          <button
            type="button"
            className="shrink-0 text-text-muted hover:text-navy"
            aria-label="Dismiss disclaimer"
            onClick={dismissDisclaimer}
          >
            ✕
          </button>
        </aside>
      )}

      {/* Hero — full width navy */}
      <section className="relative w-full overflow-hidden bg-navy text-white">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              'radial-gradient(ellipse 70% 80% at 90% 10%, rgba(196,151,58,0.22), transparent 55%), radial-gradient(ellipse 50% 60% at 0% 100%, rgba(255,255,255,0.08), transparent 50%)',
          }}
        />
        <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 sm:py-20 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div className="space-y-5 fade-up">
            <p
              className="text-[11px] font-semibold uppercase text-accent"
              style={{ letterSpacing: '3px' }}
            >
              Missing persons platform
            </p>
            <h1 className="font-display text-[40px] leading-[1.2] text-white sm:text-[56px]">
              Every second counts.
            </h1>
            <p className="max-w-lg text-lg text-white/60">
              Search active cases, share what you saw, and help families find the people they love.
            </p>
            <div className="flex flex-col gap-3 pt-1 sm:flex-row">
              <Link
                to="/report"
                className="inline-flex items-center justify-center rounded-md bg-white px-5 py-3 text-sm font-semibold text-navy transition-all hover:-translate-y-0.5 hover:bg-cream hover:shadow-lg"
              >
                Report a missing person
              </Link>
              <a
                href="#active-cases"
                className="inline-flex items-center justify-center rounded-md border border-white px-5 py-3 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-white/10"
              >
                Browse active cases
              </a>
            </div>
          </div>

          <div className="rounded-xl border border-white/15 bg-white/[0.08] px-5 py-6 backdrop-blur-sm fade-up" style={{ animationDelay: '120ms' }}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/50">
              How it works
            </p>
            <ol className="mt-4 space-y-2 text-sm text-white/80">
              {[
                ['01', 'Families publish a case with details and a photo.'],
                ['02', 'The public searches and submits location-based tips.'],
                ['03', 'Sightings appear on a map and printable flyer.'],
              ].map(([n, text]) => (
                <li
                  key={n}
                  className="flex gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-white/10"
                >
                  <span className="font-display text-lg text-accent">{n}</span>
                  <span className="self-center">{text}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* Search */}
      <section className="section-gap bg-cream">
        <div className="mx-auto max-w-[720px] px-4 sm:px-6">
          <form onSubmit={handleSearch} className="space-y-5 text-center">
            <h2 className="font-display text-3xl text-navy sm:text-4xl">Search active cases</h2>

            <div className="inline-flex rounded-full border border-border bg-white p-1 shadow-card">
              <button
                type="button"
                onClick={() => setMode('keyword')}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                  mode === 'keyword' ? 'bg-navy text-white' : 'text-text-muted hover:text-navy'
                }`}
              >
                Keyword
              </button>
              <button
                type="button"
                onClick={() => setMode('natural')}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                  mode === 'natural' ? 'bg-navy text-white' : 'text-text-muted hover:text-navy'
                }`}
              >
                Natural language
              </button>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <svg
                  className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                >
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.75" />
                  <path d="M20 20l-3.2-3.2" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
                </svg>
                <input
                  id="search"
                  className="input-field h-14 pl-12 text-base"
                  placeholder={
                    mode === 'natural'
                      ? 'e.g. missing women in Baltimore around age 30'
                      : 'Search by name or location'
                  }
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <button
                type="submit"
                className="btn-primary h-14 shrink-0 px-8"
                disabled={loading}
              >
                {loading ? 'Searching…' : 'Search'}
              </button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
              <button
                type="button"
                className="font-semibold text-text-muted underline decoration-border underline-offset-4 hover:text-navy"
                onClick={loadActive}
              >
                Clear · show all active
              </button>
              {filtersUsed && (
                <p className="text-xs text-text-muted">
                  Applied filters: {JSON.stringify(filtersUsed)}
                </p>
              )}
            </div>
          </form>
        </div>
      </section>

      {/* Active cases */}
      <section id="active-cases" className="pb-20">
        <div className="page-pad !pb-0">
          <div className="mb-6 flex items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-3xl text-navy">Active cases</h2>
              <p className="mt-1 text-sm text-text-muted">
                Open profiles awaiting tips from the public.
              </p>
            </div>
            <span className="text-sm font-semibold tabular-nums text-text-muted">
              {persons.length} shown
            </span>
          </div>

          {loading && (
            <div className="grid gap-4 md:grid-cols-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="surface-card flex gap-4 p-4">
                  <div className="skeleton h-20 w-20 shrink-0 rounded-lg" />
                  <div className="flex-1 space-y-2 py-1">
                    <div className="skeleton h-5 w-2/3 rounded" />
                    <div className="skeleton h-3 w-1/2 rounded" />
                    <div className="skeleton h-3 w-full rounded" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </p>
          )}
          {!loading && !error && persons.length === 0 && (
            <div className="surface-card px-5 py-12 text-center">
              <p className="font-display text-xl text-navy">No matching cases</p>
              <p className="mt-2 text-sm text-text-muted">
                Try a different search, or{' '}
                <Link to="/report" className="font-semibold text-navy underline underline-offset-2">
                  report a missing person
                </Link>
                .
              </p>
            </div>
          )}
          {!loading && persons.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {persons.map((p, i) => (
                <PersonCard key={p.id} person={p} index={i} />
              ))}
            </div>
          )}

          {/* More tools — collapsed */}
          <div className="mt-16 border-t border-border pt-8">
            <button
              type="button"
              className="group flex items-center gap-2 rounded-full border border-border bg-white px-4 py-2 text-sm font-semibold text-navy shadow-card transition-all hover:-translate-y-0.5 hover:border-accent/40"
              onClick={() => setMoreTools((v) => !v)}
              aria-expanded={moreTools}
            >
              More tools
              <span
                className={`inline-block text-accent transition-transform ${moreTools ? 'rotate-180' : ''}`}
              >
                ▾
              </span>
            </button>
            {moreTools && (
              <div className="mt-6 space-y-6 fade-up">
                <FaceMatchPanel />
                <div className="grid gap-4 lg:grid-cols-[1fr_320px] lg:items-start">
                  <AlertsAndMemoryPanel />
                  <LiveTipFeed />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
