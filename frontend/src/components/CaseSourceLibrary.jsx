/**
 * Read-only source library links for a case (migration 005).
 */
import { useEffect, useState } from 'react'
import { listCaseSources } from '../advancedApi.js'
import { formatEventDate, safeHttpUrl } from '../lib/caseHelpers.js'

const TYPE_LABEL = {
  agency_listing: 'Agency listing',
  news_article: 'News article',
  public_appeal: 'Public appeal',
  other: 'Other',
}

export default function CaseSourceLibrary({ personId }) {
  const [sources, setSources] = useState([])
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    listCaseSources(personId)
      .then((data) => {
        if (cancelled) return
        setSources(data.sources || [])
        setNote(data.note || '')
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Could not load sources')
      })
    return () => {
      cancelled = true
    }
  }, [personId])

  if (error) {
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
        Source library unavailable. {error}
      </p>
    )
  }

  if (!sources.length) {
    return (
      <section className="surface-card p-5">
        <h2 className="font-display text-xl text-navy">Source links</h2>
        <p className="mt-2 text-sm text-text-muted">
          {note
            ? 'No source links table yet (run migration 005), or none added for this case.'
            : 'No additional source links for this case.'}
        </p>
      </section>
    )
  }

  return (
    <section className="surface-card p-5 sm:p-6">
      <h2 className="font-display text-xl text-navy">Source links</h2>
      <p className="mt-1 text-xs text-text-muted">Linked references for this case (not scraped).</p>
      <ul className="mt-4 space-y-3">
        {sources.map((s) => {
          const href = safeHttpUrl(s.url)
          return (
            <li key={s.id} className="border-b border-border pb-3 last:border-0 last:pb-0">
              <p className="text-xs font-bold uppercase tracking-wide text-text-muted">
                {TYPE_LABEL[s.source_type] || s.source_type || 'Other'}
                {s.published_at ? ` · ${formatEventDate(s.published_at) || s.published_at}` : ''}
              </p>
              <p className="font-semibold text-navy">{s.title}</p>
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-all text-sm text-navy underline underline-offset-2"
                >
                  {href}
                </a>
              ) : (
                <p className="text-sm text-text-muted">Invalid or missing URL</p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
