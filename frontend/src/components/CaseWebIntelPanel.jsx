/**
 * CaseWebIntelPanel — runs Smart Person Search (lookup) for an existing case.
 * Shows the same intelligence report as /lookup: public web mentions, timeline, heatmap.
 */
import { useEffect, useRef, useState } from 'react'
import { lookupSearch } from '../api.js'
import ReportCard from './ReportCard.jsx'

const STATUS_MESSAGES = [
  'Searching Instagram...',
  'Scanning Facebook...',
  'Reading Reddit threads...',
  'Checking news & public web...',
  'Compiling intelligence report...',
]

const cacheKey = (personId) => `fmp-case-webintel:${personId}`

export default function CaseWebIntelPanel({ person }) {
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [statusIdx, setStatusIdx] = useState(0)
  const [progress, setProgress] = useState(8)
  const runIdRef = useRef(0)

  useEffect(() => {
    if (!busy) return undefined
    const t1 = setInterval(() => setStatusIdx((i) => (i + 1) % STATUS_MESSAGES.length), 1800)
    const t2 = setInterval(() => setProgress((p) => (p >= 92 ? 92 : p + Math.random() * 5)), 700)
    return () => {
      clearInterval(t1)
      clearInterval(t2)
    }
  }, [busy])

  async function runScan({ force = false } = {}) {
    if (!person?.name) return
    const runId = ++runIdRef.current
    setError('')
    setBusy(true)
    setProgress(8)
    setStatusIdx(0)

    if (!force) {
      try {
        const cached = sessionStorage.getItem(cacheKey(person.id))
        if (cached) {
          const parsed = JSON.parse(cached)
          if (parsed?.report_id || Array.isArray(parsed?.raw_mentions)) {
            if (runId !== runIdRef.current) return
            setReport(parsed)
            setProgress(100)
            setBusy(false)
            return
          }
        }
      } catch {
        /* ignore cache errors */
      }
    }

    try {
      // Skip huge data-URL photos on auto-scan — they slow the request a lot
      const photo =
        !force && person.photo_url?.startsWith('data:')
          ? undefined
          : person.photo_url &&
              (person.photo_url.startsWith('data:image') || person.photo_url.startsWith('http'))
            ? person.photo_url
            : undefined

      const data = await lookupSearch(
        {
          name: person.name,
          photo: photo || undefined,
        },
        { timeoutMs: 150_000 },
      )
      if (runId !== runIdRef.current) return
      setReport(data)
      setProgress(100)
      try {
        sessionStorage.setItem(cacheKey(person.id), JSON.stringify(data))
      } catch {
        /* quota */
      }
    } catch (err) {
      if (runId !== runIdRef.current) return
      const msg =
        err?.name === 'AbortError'
          ? 'Scan timed out after 2.5 minutes. Click Rescan to try again (Apify crawlers can be slow).'
          : err.message || 'Public web scan failed'
      setError(msg)
    } finally {
      if (runId === runIdRef.current) setBusy(false)
    }
  }

  // Auto-run once when the case opens (debounced so React Strict Mode doesn't abort mid-flight)
  useEffect(() => {
    if (!person?.id) return undefined
    let cancelled = false
    const timer = setTimeout(() => {
      if (!cancelled) runScan({ force: false })
    }, 150)
    return () => {
      cancelled = true
      clearTimeout(timer)
      // Invalidate in-flight UI updates from a discarded mount (Strict Mode)
      runIdRef.current += 1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [person?.id])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-navy/15 pb-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-navy/45">
            Public web intelligence
          </p>
          <h2 className="font-display text-2xl text-navy sm:text-3xl">
            Same scan as Lookup
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-navy/60">
            Apify + public sources for <span className="font-semibold text-navy">{person.name}</span>
            — Reddit, Instagram, Facebook, news, and more — merged into a sighting brief.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          disabled={busy}
          onClick={() => runScan({ force: true })}
        >
          {busy ? 'Scanning…' : report ? 'Rescan public web' : 'Scan public web'}
        </button>
      </div>

      {busy && (
        <div className="surface-panel space-y-3 p-5">
          <p className="text-sm font-semibold text-navy">{STATUS_MESSAGES[statusIdx]}</p>
          <div className="h-2 overflow-hidden bg-navy/10">
            <div
              className="h-full bg-navy transition-all duration-500"
              style={{ width: `${Math.min(progress, 95)}%` }}
            />
          </div>
          <p className="text-xs text-navy/45">
            Usually 30–90 seconds. If this passes ~2 minutes, it will time out so you can retry.
          </p>
        </div>
      )}

      {error && (
        <div className="border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p>{error}</p>
          <button
            type="button"
            className="mt-2 text-sm font-semibold underline"
            onClick={() => runScan({ force: true })}
          >
            Try again
          </button>
        </div>
      )}

      {!busy && report && <ReportCard report={report} />}

      {!busy && !report && !error && (
        <p className="text-sm text-navy/55">No public-web report yet. Click Scan to start.</p>
      )}
    </section>
  )
}
