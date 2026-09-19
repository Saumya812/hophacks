/**
 * Homepage — disclaimer, hero, search, and active cases.
 * Supports keyword filters and Gemini natural-language search.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPersons, naturalSearch } from '../api.js'
import PersonCard from '../components/PersonCard.jsx'
import FaceMatchPanel from '../components/FaceMatchPanel.jsx'

export default function Home() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('keyword') // keyword | natural
  const [filtersUsed, setFiltersUsed] = useState(null)

  async function loadActive() {
    setLoading(true)
    setError('')
    setFiltersUsed(null)
    try {
      const data = await listPersons({ status: 'active' })
      setPersons(data.persons || [])
    } catch (err) {
      setError(err.message || 'Failed to load cases')
      setPersons([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadActive()
  }, [])

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

  return (
    <div className="space-y-10">
      {/* Top-of-page legal / safety disclaimer */}
      <aside
        role="note"
        className="border border-amber-900/15 bg-[#fff8ef] px-4 py-3.5 sm:px-5"
      >
        <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#6b4e1e]">
          Important disclaimer
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-[#4a3a22]">
          FindMyPal is a community tip-sharing platform and is <strong>not</strong> affiliated
          with law enforcement, emergency services, or official missing-persons databases.
          Sightings are user-submitted and may be unverified. If you believe someone is in
          immediate danger, call your local emergency number. Always contact police to file
          or follow up on an official report. This platform must <strong>not</strong> be
          misused — including for false reports, harassment, impersonation, or sharing
          misleading information. Misuse may result in account removal and strict legal
          action.
        </p>
      </aside>

      {/* Hero — brand-forward composition */}
      <section className="relative overflow-hidden border border-navy/10 bg-navy text-white">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(135deg, rgba(255,255,255,0.06) 0%, transparent 42%),
              radial-gradient(ellipse 70% 80% at 100% 0%, rgba(154,173,196,0.25), transparent 55%)
            `,
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-8 bottom-0 top-0 w-1/3 opacity-[0.07]"
          style={{
            backgroundImage:
              'repeating-linear-gradient(90deg, #fff 0, #fff 1px, transparent 1px, transparent 28px)',
          }}
        />

        <div className="relative grid gap-8 px-5 py-10 sm:px-8 sm:py-14 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/50">
              Missing persons platform
            </p>
            <h1 className="font-display text-5xl leading-[1.05] tracking-tight text-white sm:text-6xl lg:text-7xl">
              FindMyPal
            </h1>
            <p className="max-w-lg text-base leading-relaxed text-white/75 sm:text-lg">
              Search active cases, share sightings, and help families reconnect with the people
              they love.
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link
                to="/report"
                className="inline-flex items-center justify-center rounded-sm bg-white px-5 py-2.5 text-sm font-semibold tracking-wide text-navy transition-colors hover:bg-navy-50"
              >
                Report a missing person
              </Link>
              <a
                href="#active-cases"
                className="inline-flex items-center justify-center rounded-sm border border-white/30 px-5 py-2.5 text-sm font-semibold tracking-wide text-white transition-colors hover:border-white hover:bg-white/10"
              >
                Browse active cases
              </a>
            </div>
          </div>

          <div className="border border-white/15 bg-white/5 px-5 py-5 backdrop-blur-[1px]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/45">
              How it works
            </p>
            <ol className="mt-4 space-y-3 text-sm text-white/80">
              <li className="flex gap-3">
                <span className="font-display text-lg text-white/40">01</span>
                <span>Families publish a case with details and a photo.</span>
              </li>
              <li className="flex gap-3">
                <span className="font-display text-lg text-white/40">02</span>
                <span>The public searches and submits location-based tips.</span>
              </li>
              <li className="flex gap-3">
                <span className="font-display text-lg text-white/40">03</span>
                <span>Sightings appear on a map and printable flyer.</span>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <FaceMatchPanel />

      {/* Search */}
      <section className="surface-panel p-5 sm:p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <label htmlFor="search" className="label-field">
                Search cases
              </label>
              <p className="text-sm text-navy/55">
                Look up by name or location — or describe what you remember in plain language.
              </p>
            </div>
            <div className="flex gap-1 rounded-sm border border-navy/15 bg-navy-50/60 p-1 text-sm">
              <button
                type="button"
                onClick={() => setMode('keyword')}
                className={`px-3 py-1.5 font-semibold transition-colors ${
                  mode === 'keyword'
                    ? 'bg-navy text-white'
                    : 'text-navy/65 hover:text-navy'
                }`}
              >
                Keyword
              </button>
              <button
                type="button"
                onClick={() => setMode('natural')}
                className={`px-3 py-1.5 font-semibold transition-colors ${
                  mode === 'natural'
                    ? 'bg-navy text-white'
                    : 'text-navy/65 hover:text-navy'
                }`}
              >
                Natural language
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="search"
              className="input-field"
              placeholder={
                mode === 'natural'
                  ? 'e.g. missing women in Baltimore around age 30'
                  : 'Search by name or location'
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" className="btn-primary sm:min-w-[7.5rem]" disabled={loading}>
              Search
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm">
            <button
              type="button"
              className="font-semibold text-navy/60 underline decoration-navy/25 underline-offset-4 transition-colors hover:text-navy"
              onClick={loadActive}
            >
              Clear · show all active
            </button>
            {filtersUsed && (
              <p className="text-xs text-navy/50">
                Applied filters: {JSON.stringify(filtersUsed)}
              </p>
            )}
          </div>
        </form>
      </section>

      {/* Case list */}
      <section id="active-cases">
        <div className="mb-4 flex items-end justify-between gap-3 border-b border-navy/15 pb-3">
          <div>
            <h2 className="font-display text-3xl text-navy">Active cases</h2>
            <p className="mt-1 text-sm text-navy/55">Open profiles awaiting tips from the public.</p>
          </div>
          <span className="pb-1 text-sm font-semibold tabular-nums text-navy/45">
            {persons.length} shown
          </span>
        </div>

        {loading && (
          <div className="surface-panel px-5 py-12 text-center text-navy/55">Loading cases…</div>
        )}
        {error && (
          <p className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>
        )}
        {!loading && !error && persons.length === 0 && (
          <div className="surface-panel px-5 py-12 text-center">
            <p className="font-display text-xl text-navy/70">No matching cases</p>
            <p className="mt-2 text-sm text-navy/55">
              Try a different search, or{' '}
              <Link to="/report" className="font-semibold text-navy underline underline-offset-2">
                report a missing person
              </Link>
              .
            </p>
          </div>
        )}
        {!loading && persons.length > 0 && (
          <div className="surface-panel overflow-hidden divide-y-0">
            {persons.map((p) => (
              <PersonCard key={p.id} person={p} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
