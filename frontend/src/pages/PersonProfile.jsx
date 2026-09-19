/**
 * Person profile page — details, AI summary, timeline, map, flyer PDF.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPerson, listSightings, getCaseSummary, refreshCaseSummary } from '../api.js'
import SightingsMap from '../components/SightingsMap.jsx'
import FlyerButton from '../components/FlyerButton.jsx'

export default function PersonProfile() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [sightings, setSightings] = useState([])
  const [summary, setSummary] = useState(null)
  const [summaryBusy, setSummaryBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [p, s] = await Promise.all([getPerson(id), listSightings(id)])
        if (cancelled) return
        setPerson(p)
        setSightings(s.sightings || [])
        // Load / generate summary in background
        getCaseSummary(id)
          .then((sum) => {
            if (!cancelled) setSummary(sum)
          })
          .catch(() => {
            /* summary is optional */
          })
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [id])

  async function onRefreshSummary() {
    setSummaryBusy(true)
    try {
      const sum = await refreshCaseSummary(id)
      setSummary(sum)
    } catch (err) {
      setError(err.message || 'Could not refresh summary')
    } finally {
      setSummaryBusy(false)
    }
  }

  if (loading) return <p className="text-navy/60">Loading profile…</p>
  if (error && !person) {
    return (
      <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
    )
  }
  if (!person) return null

  const timeline = [
    {
      id: 'last-seen',
      label: 'Last known',
      when: person.last_seen_date,
      text: person.last_seen_location,
      kind: 'last',
    },
    ...sightings.map((s) => ({
      id: s.id,
      label: s.family_review_flag
        ? `Sighting · credibility ${s.credibility_score ?? '—'}/10 · family review`
        : `Sighting · credibility ${s.credibility_score ?? '—'}/10 · reporter ${s.confidence_level}/5`,
      when: s.date_time,
      text: s.description,
      kind: 'sighting',
      high: Boolean(s.family_review_flag),
      reasons: s.credibility_reasons,
    })),
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-6 sm:flex-row">
        <div className="h-56 w-full shrink-0 overflow-hidden bg-navy-100 sm:h-64 sm:w-52">
          {person.photo_url ? (
            <img
              src={person.photo_url}
              alt={person.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-sm text-navy/40">
              No photo
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-navy/50">
              {person.status} case
            </p>
            <h1 className="font-display text-3xl text-navy sm:text-4xl">{person.name}</h1>
            <p className="mt-1 text-navy/70">
              Age {person.age}
              {person.gender ? ` · ${person.gender}` : ''}
            </p>
          </div>

          <p className="text-navy/85">{person.description}</p>

          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold text-navy">Last seen location</dt>
              <dd className="text-navy/75">{person.last_seen_location}</dd>
            </div>
            <div>
              <dt className="font-semibold text-navy">Last seen date</dt>
              <dd className="text-navy/75">{person.last_seen_date}</dd>
            </div>
            {person.police_report_number && (
              <div>
                <dt className="font-semibold text-navy">Police report #</dt>
                <dd className="text-navy/75">{person.police_report_number}</dd>
              </div>
            )}
          </dl>

          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={`/tip/${person.id}`} className="btn-primary">
              Submit a tip
            </Link>
            <FlyerButton person={person} />
          </div>
        </div>
      </div>

      {/* AI Case Summarizer */}
      <section className="surface-panel p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-navy/45">
              AI case summary
            </p>
            <h2 className="font-display text-2xl text-navy">Plain-English brief</h2>
          </div>
          <button
            type="button"
            className="btn-secondary"
            onClick={onRefreshSummary}
            disabled={summaryBusy}
          >
            {summaryBusy ? 'Updating…' : 'Refresh summary'}
          </button>
        </div>
        <p className="text-sm leading-relaxed text-navy/80">
          {summary?.summary ||
            person.ai_summary ||
            'Summary will appear after tips are available, or click Refresh.'}
        </p>
        {summary && (
          <p className="mt-2 text-xs text-navy/45">
            Engine: {summary.engine} · based on {summary.sighting_count} tip
            {summary.sighting_count === 1 ? '' : 's'}
            {summary.generated_at ? ` · ${new Date(summary.generated_at).toLocaleString()}` : ''}
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-navy">Sightings map</h2>
        <SightingsMap
          lastSeenLocation={person.last_seen_location}
          sightings={sightings}
        />
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-navy">Timeline</h2>
        {timeline.length === 0 ? (
          <p className="text-navy/60">No events yet.</p>
        ) : (
          <ol className="space-y-0 border-l-2 border-navy/20 pl-4">
            {timeline.map((item) => (
              <li key={item.id} className="relative pb-5">
                <span
                  className={`absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full ${
                    item.kind === 'last'
                      ? 'bg-red-600'
                      : item.high
                        ? 'bg-emerald-600'
                        : 'bg-blue-600'
                  }`}
                />
                <p className="text-xs font-semibold uppercase tracking-wide text-navy/50">
                  {item.label}
                </p>
                <p className="text-sm text-navy/55">
                  {item.when ? new Date(item.when).toLocaleString() : '—'}
                </p>
                <p className="mt-1 text-navy/85">{item.text}</p>
                {item.reasons && (
                  <p className="mt-1 text-xs text-navy/50">{item.reasons}</p>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}
