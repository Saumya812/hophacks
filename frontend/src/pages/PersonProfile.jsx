/**
 * Person profile — navy hero + tabbed Overview / Tips & Map / Web Intel / Family Tools.
 */
import { Component, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPerson, listSightings, getCaseSummary, refreshCaseSummary, API_BASE } from '../api.js'
import SightingsMap from '../components/SightingsMap.jsx'
import FlyerButton from '../components/FlyerButton.jsx'
import CaseToolsPanel from '../components/CaseToolsPanel.jsx'
import CaseWebIntelPanel from '../components/CaseWebIntelPanel.jsx'
import DensityHeatMap from '../components/DensityHeatMap.jsx'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tips', label: 'Tips & Map' },
  { id: 'intel', label: 'Web Intel' },
  { id: 'family', label: 'Family Tools' },
]

class PanelErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <p className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          {this.props.fallback || 'This panel failed to load.'}{' '}
          <button
            type="button"
            className="font-semibold underline"
            onClick={() => this.setState({ error: null })}
          >
            Retry
          </button>
        </p>
      )
    }
    return this.props.children
  }
}

export default function PersonProfile() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [sightings, setSightings] = useState([])
  const [summary, setSummary] = useState(null)
  const [summaryBusy, setSummaryBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('overview')
  const [shareMsg, setShareMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const p = await getPerson(id)
        if (cancelled) return
        setPerson(p)
        setLoading(false)

        try {
          const s = await listSightings(id)
          if (!cancelled) setSightings(s.sightings || [])
        } catch {
          if (!cancelled) setSightings([])
        }

        getCaseSummary(id)
          .then((sum) => {
            if (!cancelled) setSummary(sum)
          })
          .catch(() => {})
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load profile')
          setLoading(false)
        }
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

  async function shareCase() {
    const url = window.location.href
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${person.name} — FindMyPal`,
          text: `Help find ${person.name}`,
          url,
        })
        setShareMsg('Shared')
      } else {
        await navigator.clipboard.writeText(url)
        setShareMsg('Link copied')
      }
    } catch {
      try {
        await navigator.clipboard.writeText(url)
        setShareMsg('Link copied')
      } catch {
        setShareMsg('Could not share')
      }
    }
    setTimeout(() => setShareMsg(''), 2500)
  }

  if (loading) {
    return <p className="page-pad text-text-muted">Loading profile…</p>
  }
  if (error && !person) {
    return (
      <p className="page-pad rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
        {error}
      </p>
    )
  }
  if (!person) return null

  const isActive = (person.status || '').toLowerCase() === 'active'
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
      location: null,
      confidence: s.confidence_level,
    })),
  ]

  return (
    <div className="bg-cream pb-20">
      {error && (
        <p className="mx-auto max-w-6xl px-4 pt-4 text-sm text-amber-900 sm:px-6">{error}</p>
      )}

      {/* Hero */}
      <section className="w-full bg-navy text-white">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-10 sm:flex-row sm:items-center sm:px-6 sm:py-12">
          <div className="gold-ring h-24 w-24 shrink-0 overflow-hidden rounded-full border-[3px] border-accent bg-navy-light">
            {person.photo_url ? (
              <img src={person.photo_url} alt={person.name} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center font-display text-2xl text-white/40">
                {(person.name || '?').charAt(0)}
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1 space-y-3">
            {isActive && (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-emerald-300">
                <span className="pulse-dot h-2 w-2 rounded-full bg-success" />
                Active
              </span>
            )}
            <h1 className="font-display text-3xl text-white sm:text-4xl">{person.name}</h1>
            <p className="text-sm text-white/60">
              Age {person.age}
              {person.gender ? ` · ${person.gender}` : ''}
            </p>
            <p className="text-[13px] font-medium text-accent">
              Last seen · {person.last_seen_location}
              {person.last_seen_date ? ` · ${person.last_seen_date}` : ''}
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link to={`/tip/${person.id}`} className="btn-gold">
                Submit a tip
              </Link>
              <button type="button" className="btn-outline-white" onClick={shareCase}>
                Share case
              </button>
              {shareMsg && <span className="self-center text-xs text-white/60">{shareMsg}</span>}
            </div>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <div className="sticky top-0 z-20 border-b border-border bg-cream/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 sm:px-6">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`shrink-0 border-b-2 px-4 py-3.5 text-sm font-semibold transition-colors ${
                tab === t.id
                  ? 'border-navy text-navy'
                  : 'border-transparent text-text-muted hover:text-navy'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="page-pad pt-8 fade-up" key={tab}>
        {tab === 'overview' && (
          <div className="space-y-6">
            <section className="surface-card p-5 sm:p-6">
              <h2 className="font-display text-2xl text-navy">Description</h2>
              <p className="mt-3 leading-relaxed text-text-primary">{person.description}</p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-navy">Last seen location</dt>
                  <dd className="text-text-muted">{person.last_seen_location}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-navy">Last seen date</dt>
                  <dd className="text-text-muted">{person.last_seen_date}</dd>
                </div>
                {person.police_report_number && (
                  <div>
                    <dt className="font-semibold text-navy">Police report #</dt>
                    <dd className="text-text-muted">{person.police_report_number}</dd>
                  </div>
                )}
              </dl>
            </section>

            <section className="surface-card border-l-4 border-l-navy p-5 sm:p-6">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">
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
              <p className="text-sm leading-relaxed text-text-primary">
                {summary?.summary ||
                  person.ai_summary ||
                  'Summary will appear after tips are available, or click Refresh.'}
              </p>
              {summary && (
                <p className="mt-2 text-xs text-text-muted">
                  Engine: {summary.engine} · based on {summary.sighting_count} tip
                  {summary.sighting_count === 1 ? '' : 's'}
                  {summary.generated_at
                    ? ` · ${new Date(summary.generated_at).toLocaleString()}`
                    : ''}
                </p>
              )}
            </section>

            <section className="surface-card p-5 sm:p-6">
              <h2 className="font-display text-2xl text-navy">Timeline of updates</h2>
              {timeline.length === 0 ? (
                <p className="mt-3 text-text-muted">No events yet.</p>
              ) : (
                <ol className="mt-4 space-y-0 border-l-2 border-border pl-4">
                  {timeline.map((item) => (
                    <li key={item.id} className="relative pb-5">
                      <span
                        className={`absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full ${
                          item.kind === 'last'
                            ? 'bg-danger'
                            : item.high
                              ? 'bg-success'
                              : 'bg-navy'
                        }`}
                      />
                      <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                        {item.label}
                      </p>
                      <p className="text-sm text-text-muted">
                        {item.when ? new Date(item.when).toLocaleString() : '—'}
                      </p>
                      <p className="mt-1 text-text-primary">{item.text}</p>
                      {item.reasons && (
                        <p className="mt-1 text-xs text-text-muted">{item.reasons}</p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        )}

        {tab === 'tips' && (
          <div className="space-y-6">
            <section className="space-y-3">
              <h2 className="font-display text-2xl text-navy">Community tips map</h2>
              <PanelErrorBoundary fallback="Map failed to render.">
                <SightingsMap
                  key={`map-${person.id}`}
                  lastSeenLocation={person.last_seen_location}
                  sightings={sightings}
                />
              </PanelErrorBoundary>
            </section>

            <section className="space-y-3">
              <h2 className="font-display text-2xl text-navy">Live sightings heatmap</h2>
              <PanelErrorBoundary fallback="Heatmap failed to render.">
                <DensityHeatMap
                  points={(sightings || []).map((s) => ({
                    lat: Number(s.location_lat),
                    lng: Number(s.location_lng),
                    weight:
                      s.credibility_score != null
                        ? Math.max(1, Number(s.credibility_score) / 3)
                        : 1,
                    label: s.description || 'Community tip',
                    date: s.date_time || '',
                  }))}
                  lastSeenLocation={person.last_seen_location}
                  title={`Heatmap · ${person.name}`}
                />
                <p className="text-xs text-text-muted">
                  Marimo data:{' '}
                  <a
                    className="underline"
                    href={`${API_BASE}/analytics/heatmap/${person.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    /analytics/heatmap/{person.id}
                  </a>
                </p>
              </PanelErrorBoundary>
            </section>

            <section className="space-y-3">
              <h2 className="font-display text-2xl text-navy">Tips</h2>
              {sightings.length === 0 ? (
                <p className="surface-card p-5 text-text-muted">
                  No tips yet. Be the first to{' '}
                  <Link to={`/tip/${person.id}`} className="font-semibold text-navy underline">
                    submit a tip
                  </Link>
                  .
                </p>
              ) : (
                <ul className="space-y-3">
                  {[...sightings]
                    .sort((a, b) => new Date(b.date_time || 0) - new Date(a.date_time || 0))
                    .map((s) => (
                      <li key={s.id} className="surface-card p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-navy/10 px-2.5 py-0.5 text-[11px] font-bold uppercase text-navy">
                            Confidence {s.confidence_level}/5
                          </span>
                          {s.credibility_score != null && (
                            <span className="text-xs text-text-muted">
                              Credibility {s.credibility_score}/10
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-sm font-medium text-accent">
                          {s.location_lat != null && s.location_lng != null
                            ? `${Number(s.location_lat).toFixed(4)}, ${Number(s.location_lng).toFixed(4)}`
                            : 'Location on file'}
                        </p>
                        <p className="mt-1 text-xs text-text-muted">
                          {s.date_time ? new Date(s.date_time).toLocaleString() : '—'}
                        </p>
                        <p className="mt-2 text-sm text-text-primary">{s.description}</p>
                      </li>
                    ))}
                </ul>
              )}
            </section>
          </div>
        )}

        {tab === 'intel' && (
          <PanelErrorBoundary fallback="Public web intelligence failed.">
            <CaseWebIntelPanel person={person} autoStart={false} />
          </PanelErrorBoundary>
        )}

        {tab === 'family' && (
          <div className="space-y-6">
            <section className="surface-card p-5">
              <h2 className="font-display text-xl text-navy">Download flyer</h2>
              <p className="mt-1 text-sm text-text-muted">
                Printable PDF with photo, details, and a QR code to this profile.
              </p>
              <div className="mt-3">
                <FlyerButton person={person} />
              </div>
            </section>
            <PanelErrorBoundary fallback="Case tools failed.">
              <CaseToolsPanel person={person} onPersonChange={setPerson} />
            </PanelErrorBoundary>
          </div>
        )}
      </div>
    </div>
  )
}
