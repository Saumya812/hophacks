/**
 * ReportCard — Smart Person Search intelligence brief.
 * Sections: summary, timeline, heatmap, raw mentions, PDF download.
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
  reddit: '#FF4500',
  youtube: '#FF0000',
  news: '#1a2b4a',
  google: '#1a2b4a',
  web: '#4d6786',
}

function confidenceClass(level) {
  const c = (level || 'low').toLowerCase()
  if (c === 'high') return 'border-l-emerald-600 bg-emerald-50/80'
  if (c === 'medium') return 'border-l-amber-500 bg-amber-50/70'
  return 'border-l-amber-300 bg-amber-50/40'
}

/** Strip bidi marks and normalize mixed date formats for display. */
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
        // Prefer MDY (US); if month invalid try DMY
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
    <span
      className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider"
      style={{ color }}
    >
      <span className="inline-block h-2 w-2 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  )
}

export default function ReportCard({ report }) {
  const [platformFilter, setPlatformFilter] = useState('all')
  const [rawOpen, setRawOpen] = useState(false)

  const summary = report?.summary || {}
  const sightings = report?.sightings || []
  const locations = report?.locations || []
  const rawMentions = report?.raw_mentions || []
  const sourcesStatus = report?.sources_status || {}

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

  // Auto-expand raw mentions when filters found nothing useful
  useEffect(() => {
    if (sparse) setRawOpen(true)
  }, [sparse])

  if (empty) {
    return (
      <div className="surface-panel space-y-4 p-6 text-center sm:p-8">
        <p className="font-display text-2xl text-navy">No public mentions found</p>
        <p className="mx-auto max-w-lg text-sm leading-relaxed text-navy/65">
          We could not find meaningful public results for <strong>{summary.name}</strong>.
          Try a different spelling, include a middle name, or check that optional search API
          keys are configured on the server.
        </p>
        <ul className="mx-auto max-w-md list-disc space-y-1 px-6 text-left text-sm text-navy/60">
          <li>Use the person&apos;s commonly published name</li>
          <li>Add SERPAPI_KEY / NEWSAPI_KEY for deeper coverage</li>
          <li>File an official police report if you have not already</li>
        </ul>
      </div>
    )
  }

  const dateStart = formatReportDate(summary.date_range?.start)
  const dateEnd = formatReportDate(summary.date_range?.end)
  const engine = report?.extraction_engine

  return (
    <div className="space-y-8">
      {sparse && (
        <aside className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p className="font-semibold">Limited public index results</p>
          <p className="mt-1">
            Search found indexed pages, but little or no location/time sighting language.
            Social/profile hits are listed as low-confidence mentions and under Raw mentions.
            This is not proof of a sighting. Add NEWSAPI_KEY / SERPAPI_KEY for deeper coverage,
            and always work with police on real cases.
          </p>
        </aside>
      )}

      {/* SUMMARY */}
      <section className="surface-panel overflow-hidden">
        <div className="border-b border-navy/10 bg-navy px-5 py-3 text-white">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/55">
            Summary
          </p>
          <h2 className="font-display text-2xl sm:text-3xl">{summary.name}</h2>
        </div>
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-start">
          <div className="h-28 w-24 shrink-0 overflow-hidden bg-navy-100 ring-1 ring-navy/10">
            {summary.photo_data_url ? (
              <img
                src={summary.photo_data_url}
                alt={summary.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-navy/40">
                No photo
              </div>
            )}
          </div>
          <dl className="grid flex-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-navy/45">
                Mentions found
              </dt>
              <dd className="mt-1 font-display text-2xl text-navy">
                {summary.total_mentions ?? sightings.length}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-navy/45">
                Date range
              </dt>
              <dd className="mt-1 text-navy/80">
                {dateStart === '—' && dateEnd === '—'
                  ? 'Not determined'
                  : `${dateStart} → ${dateEnd}`}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wider text-navy/45">
                Top location
              </dt>
              <dd className="mt-1 text-navy/80">
                {summary.most_frequent_location || 'Not determined'}
              </dd>
            </div>
          </dl>
        </div>
        {engine && engine !== 'gemini' ? (
          <div className="border-t border-amber-200 bg-amber-50 px-5 py-2 text-xs text-amber-950">
            Extractor: <strong>{engine}</strong>
            {engine === 'heuristic_fallback'
              ? ' — Gemini quota hit; using strict name-match fallback. Results may be fewer until API quota resets.'
              : ' — rule-based extract (Gemini not configured).'}
            {report?.raw_count != null ? ` · ${report.raw_count} raw indexed hits` : ''}
          </div>
        ) : null}
        {Object.keys(sourcesStatus).length > 0 && (
          <div className="border-t border-navy/10 px-5 py-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-navy/45">
              Sources queried
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(sourcesStatus).map(([k, v]) => (
                <span
                  key={k}
                  className="border border-navy/10 bg-navy-50 px-2 py-1 text-[11px] text-navy/70"
                >
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* TIMELINE */}
      <section className="space-y-3">
        <div className="border-b border-navy/15 pb-2">
          <h3 className="font-display text-2xl text-navy">Sighting timeline</h3>
          <p className="text-sm text-navy/55">
            Green = high confidence · Yellow = medium / low
          </p>
        </div>
        {sightings.length === 0 ? (
          <p className="text-sm text-navy/60">
            Raw mentions were found, but none passed location / time / description filters.
          </p>
        ) : (
          <ol className="space-y-3">
            {sightings.map((s, idx) => (
              <li
                key={`${s.url}-${idx}`}
                className={`border border-navy/10 border-l-4 px-4 py-3 ${confidenceClass(s.confidence)}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <PlatformBadge source={s.source} />
                  <span className="text-xs font-semibold uppercase tracking-wide text-navy/50">
                    {(s.confidence || 'low').toUpperCase()} ·{' '}
                    {formatReportDate(s.date) === '—' ? 'Undated' : formatReportDate(s.date)}
                  </span>
                </div>
                {s.location && (
                  <p className="mt-1 text-sm font-semibold text-navy/75">
                    Location: {s.location}
                  </p>
                )}
                <p className="mt-2 text-sm leading-relaxed text-navy/85">
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
            ))}
          </ol>
        )}
      </section>

      <LookupLocationHeatmap
        locations={locations}
        sightings={sightings}
        rawMentions={rawMentions}
      />

      {/* RAW MENTIONS */}
      <section className="surface-panel">
        <button
          type="button"
          className="flex w-full items-center justify-between px-5 py-4 text-left"
          onClick={() => setRawOpen((v) => !v)}
        >
          <div>
            <h3 className="font-display text-xl text-navy">Raw mentions</h3>
            <p className="text-sm text-navy/55">{rawMentions.length} indexed results</p>
          </div>
          <span className="text-sm font-semibold text-navy/60">
            {rawOpen ? 'Collapse' : 'Expand'}
          </span>
        </button>
        {rawOpen && (
          <div className="border-t border-navy/10 px-5 pb-5">
            <div className="flex flex-wrap gap-2 py-4">
              {platforms.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPlatformFilter(p)}
                  className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wide ${
                    platformFilter === p
                      ? 'bg-navy text-white'
                      : 'border border-navy/15 text-navy/70 hover:border-navy'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <ul className="max-h-96 space-y-3 overflow-y-auto">
              {filteredRaw.map((m, idx) => (
                <li key={`${m.url}-${idx}`} className="border-b border-navy/10 pb-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <PlatformBadge source={m.source} />
                    <span className="text-xs text-navy/45">{m.date || '—'}</span>
                  </div>
                  <p className="mt-1 text-navy/80">{m.snippet || m.title}</p>
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
      <section className="flex flex-wrap items-center justify-between gap-3 border border-navy/10 bg-white/90 px-5 py-4">
        <div>
          <p className="font-display text-lg text-navy">Download report</p>
          <p className="text-sm text-navy/55">PDF includes summary, timeline, locations, and raw sample.</p>
        </div>
        {pdfUrl ? (
          <a href={pdfUrl} className="btn-primary" target="_blank" rel="noreferrer">
            Export as PDF
          </a>
        ) : (
          <button type="button" className="btn-primary" disabled>
            Export as PDF
          </button>
        )}
      </section>
    </div>
  )
}
