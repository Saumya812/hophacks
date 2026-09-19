/**
 * ReportCard — Smart Person Search intelligence brief (visual redesign).
 */
import { useEffect, useMemo, useState } from 'react'
import { API_BASE } from '../api.js'
import LookupLocationHeatmap from './LookupLocationHeatmap.jsx'

const PLATFORM_COLORS = {
  instagram: '#C13584',
  facebook: '#1877F2',
  tiktok: '#111111',
  x: '#111111',
  twitter: '#111111',
  reddit: '#ff4500',
  youtube: '#dc2626',
  news: '#1a2b4a',
  google: '#1a2b4a',
  web: '#6b7280',
}

function confidenceBadge(level) {
  const c = (level || 'low').toLowerCase()
  if (c === 'high') return 'conf-high'
  if (c === 'medium') return 'conf-medium'
  return 'conf-low'
}

function formatReportDate(raw) {
  if (!raw) return '—'
  const cleaned = String(raw).replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, '').trim()
  if (!cleaned) return '—'

  const months = {
    jan: 0, january: 0, feb: 1, february: 1, mar: 2, march: 2, apr: 3, april: 3,
    may: 4, jun: 5, june: 5, jul: 6, july: 6, aug: 7, august: 7, sep: 8, september: 8,
    oct: 9, october: 9, nov: 10, november: 10, dec: 11, december: 11,
  }

  let d = null
  const iso = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) d = new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]))

  if (!d || Number.isNaN(d.getTime())) {
    const named = cleaned.match(/^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$/)
    if (named && months[named[1].toLowerCase()] != null) {
      d = new Date(Number(named[3]), months[named[1].toLowerCase()], Number(named[2]))
    }
  }

  if (!d || Number.isNaN(d.getTime())) {
    const slash = cleaned.match(/^(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})$/)
    if (slash) {
      let a = Number(slash[1])
      let b = Number(slash[2])
      let c = Number(slash[3])
      if (a >= 1900) d = new Date(a, b - 1, c)
      else {
        const year = c < 100 ? 2000 + c : c
        if (a >= 1 && a <= 12) d = new Date(year, a - 1, b)
        else d = new Date(year, b - 1, a)
      }
    }
  }

  if (!d || Number.isNaN(d.getTime())) return cleaned
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function PlatformBadge({ source }) {
  const label = (source || 'web').toLowerCase()
  const color = PLATFORM_COLORS[label] || PLATFORM_COLORS.web
  return (
    <span className="platform-pill" style={{ background: color }}>
      {label}
    </span>
  )
}

export default function ReportCard({ report }) {
  const [platformFilter, setPlatformFilter] = useState('all')
  const [rawOpen, setRawOpen] = useState(false)

  const summary = report?.summary || {}
  const sightings = report?.sightings || []
  const claims = report?.claims || []
  const locations = report?.locations || []
  const rawMentions = report?.raw_mentions || []
  const sourcesStatus = report?.sources_status || {}

  const visibleSources = useMemo(() => {
    return Object.entries(sourcesStatus).filter(([k, v]) => {
      const key = String(k).toLowerCase()
      const val = String(v || '').toLowerCase()
      if (key.startsWith('apify')) return false
      if (val.includes('0 hits')) return false
      if (val.includes('skipped')) return false
      return true
    })
  }, [sourcesStatus])

  const platforms = useMemo(() => {
    const set = new Set(rawMentions.map((m) => (m.source || 'web').toLowerCase()))
    return ['all', ...Array.from(set).sort()]
  }, [rawMentions])

  const filteredRaw = useMemo(() => {
    if (platformFilter === 'all') return rawMentions
    return rawMentions.filter((m) => (m.source || '').toLowerCase() === platformFilter)
  }, [rawMentions, platformFilter])

  const pdfUrl = report?.report_id
    ? `${API_BASE}/lookup/report/${report.report_id}/pdf`
    : null

  const empty = report?.empty || (sightings.length === 0 && rawMentions.length === 0)
  const sparse = !empty && sightings.length === 0 && rawMentions.length > 0

  useEffect(() => {
    if (sparse) setRawOpen(true)
  }, [sparse])

  if (empty) {
    return (
      <div className="surface-card space-y-4 p-6 text-center sm:p-8">
        <p className="font-display text-2xl text-navy">No public mentions found</p>
        <p className="mx-auto max-w-lg text-sm leading-relaxed text-text-muted">
          We could not find meaningful public results for <strong>{summary.name}</strong>.
          Try a different spelling, include a middle name, or check that optional search API
          keys are configured on the server.
        </p>
      </div>
    )
  }

  const dateStart = formatReportDate(summary.date_range?.start)
  const dateEnd = formatReportDate(summary.date_range?.end)
  const engine = report?.extraction_engine

  return (
    <div className="space-y-8">
      {sparse && (
        <aside className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="font-semibold">Limited public index results</p>
          <p className="mt-1">
            Search found indexed pages, but little or no location/time sighting language.
            This is not proof of a sighting.
          </p>
        </aside>
      )}

      {/* SUMMARY — navy card */}
      <section className="overflow-hidden rounded-xl bg-navy text-white shadow-card">
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
          <div className="h-16 w-16 shrink-0 overflow-hidden rounded-full border-2 border-accent bg-navy-light">
            {summary.photo_data_url ? (
              <img
                src={summary.photo_data_url}
                alt={summary.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-white/40">
                No photo
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/50">
              Summary
            </p>
            <h2 className="font-display text-2xl sm:text-3xl">{summary.name}</h2>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-white/45">Mentions</dt>
                <dd className="font-display text-xl">
                  {summary.total_mentions ?? sightings.length}
                </dd>
              </div>
              <div>
                <dt className="text-white/45">Date range</dt>
                <dd className="text-white/85">
                  {dateStart === '—' && dateEnd === '—'
                    ? 'Not determined'
                    : `${dateStart} → ${dateEnd}`}
                </dd>
              </div>
              <div>
                <dt className="text-white/45">Top location</dt>
                <dd className="text-accent">
                  {summary.most_frequent_location || 'Not determined'}
                </dd>
              </div>
            </dl>
          </div>
        </div>
        {engine && engine !== 'gemini' ? (
          <div className="border-t border-white/10 bg-navy-dark/40 px-5 py-2 text-xs text-amber-200">
            Extractor: <strong>{engine}</strong>
            {report?.raw_count != null ? ` · ${report.raw_count} raw indexed hits` : ''}
          </div>
        ) : null}
        {visibleSources.length > 0 && (
          <div className="border-t border-white/10 px-5 py-3">
            <div className="flex flex-wrap gap-2">
              {visibleSources.map(([k, v]) => (
                <span
                  key={k}
                  className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-white/70"
                >
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Sighting claims */}
      <section className="space-y-3">
        <div>
          <h3 className="font-display text-2xl text-navy">Sighting claims</h3>
          <p className="text-sm text-text-muted">
            Witness-style claims only. News “last seen” reports are filtered out.
          </p>
        </div>
        {claims.length === 0 ? (
          <p className="text-sm text-text-muted">
            No witness sighting claims yet. Official news stays under All extracted mentions.
          </p>
        ) : (
          <ol className="space-y-3">
            {claims.map((c, idx) => (
              <li key={`claim-${c.url || idx}-${idx}`} className="surface-card p-4 text-sm">
                <p className="leading-relaxed text-text-primary">
                  {c.claim_summary ||
                    [
                      c.username ? `@${c.username}` : 'Someone',
                      `on ${c.source || 'web'}`,
                      'claims to have seen the person',
                      c.date ? `on ${formatReportDate(c.date)}` : null,
                      c.time ? `at around ${c.time}` : null,
                      c.location ? `near ${c.location}` : null,
                    ]
                      .filter(Boolean)
                      .join(' ')}
                </p>
                {c.quote ? (
                  <p className="mt-1 text-text-muted">&ldquo;{c.quote}&rdquo;</p>
                ) : null}
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <PlatformBadge source={c.source} />
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${confidenceBadge(c.confidence)}`}
                  >
                    {c.confidence || 'low'}
                  </span>
                  {c.url ? (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-semibold text-navy underline underline-offset-2"
                    >
                      Open source
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* Timeline */}
      <section className="space-y-3">
        <div>
          <h3 className="font-display text-2xl text-navy">All extracted mentions</h3>
          <p className="text-sm text-text-muted">Chronological · platform + confidence</p>
        </div>
        {sightings.length === 0 ? (
          <p className="text-sm text-text-muted">
            Raw mentions were found, but none passed location / time filters.
          </p>
        ) : (
          <ol className="space-y-3">
            {sightings.map((s, idx) => {
              const conf = (s.confidence || 'low').toLowerCase()
              const border =
                conf === 'high'
                  ? 'border-l-4 border-l-gold'
                  : conf === 'medium'
                    ? 'border-l-4 border-l-misty'
                    : 'border-l-4 border-l-border'
              return (
              <li key={`${s.url}-${idx}`} className={`surface-card p-4 ${border}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <PlatformBadge source={s.source} />
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-md px-2 py-0.5 text-[11px] font-bold uppercase ${confidenceBadge(s.confidence)}`}
                    >
                      {s.confidence || 'low'}
                    </span>
                    <span className="text-xs text-text-muted">
                      {formatReportDate(s.date) === '—' ? 'Undated' : formatReportDate(s.date)}
                    </span>
                  </div>
                </div>
                {s.location && (
                  <p className="mt-2 text-sm font-semibold text-accent">{s.location}</p>
                )}
                <p className="mt-2 text-sm leading-relaxed text-text-primary">
                  &ldquo;{s.quote}&rdquo;
                </p>
                {s.url && (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-xs font-semibold text-navy underline underline-offset-2"
                  >
                    Open source
                  </a>
                )}
              </li>
              )
            })}
          </ol>
        )}
      </section>

      <LookupLocationHeatmap
        locations={locations}
        sightings={sightings}
        rawMentions={rawMentions}
      />

      {/* RAW MENTIONS */}
      <section className="surface-card">
        <button
          type="button"
          className="flex w-full items-center justify-between px-5 py-4 text-left"
          onClick={() => setRawOpen((v) => !v)}
        >
          <div>
            <h3 className="font-display text-xl text-navy">Raw mentions</h3>
            <p className="text-sm text-text-muted">{rawMentions.length} indexed results</p>
          </div>
          <span className="text-sm font-semibold text-text-muted">
            {rawOpen ? 'Collapse' : 'Expand'}
          </span>
        </button>
        {rawOpen && (
          <div className="border-t border-border px-5 pb-5">
            <div className="flex flex-wrap gap-2 py-4">
              {platforms.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPlatformFilter(p)}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wide ${
                    platformFilter === p
                      ? 'bg-navy text-white'
                      : 'border border-border text-text-muted hover:border-navy'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <ul className="max-h-96 space-y-3 overflow-y-auto">
              {filteredRaw.map((m, idx) => (
                <li key={`${m.url}-${idx}`} className="border-b border-border pb-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <PlatformBadge source={m.source} />
                    <span className="text-xs text-text-muted">{m.date || '—'}</span>
                  </div>
                  <p className="mt-1 text-text-primary">{m.snippet || m.title}</p>
                  {m.url && (
                    <a
                      href={m.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-block text-xs text-navy underline"
                    >
                      {m.url}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* DOWNLOAD */}
      <section className="flex flex-col items-stretch gap-3 pb-4 sm:items-end">
        {pdfUrl ? (
          <a
            href={pdfUrl}
            className="btn-gold h-12 w-full justify-center sm:w-auto sm:px-8"
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
        ) : (
          <button type="button" className="btn-gold h-12" disabled>
            Download PDF
          </button>
        )}
      </section>
    </div>
  )
}
