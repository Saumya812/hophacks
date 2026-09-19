/**
 * Compact original listing panel (community-provided — not a Verified badge).
 */
import { formatEventDate, safeHttpUrl } from '../lib/caseHelpers.js'

export default function OriginalSourcePanel({ person }) {
  const url = safeHttpUrl(person?.source_listing_url)
  const agency = (person?.source_agency_name || '').trim()
  const extNo = (person?.external_case_number || '').trim()
  const checked = formatEventDate(person?.source_last_checked_at)
  const hasAny = Boolean(url || agency || extNo || checked)

  return (
    <section className="surface-card border-l-4 border-l-accent/60 p-5 sm:p-6">
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">
        Original case source
      </p>
      <h2 className="mt-1 font-display text-xl text-navy">Where this case was listed</h2>
      <p className="mt-1 text-xs text-text-muted">
        Community-provided listing info — not an automatic verification badge.
      </p>

      {!hasAny ? (
        <p className="mt-4 text-sm text-text-muted">Original source not provided.</p>
      ) : (
        <dl className="mt-4 space-y-2 text-sm">
          {agency && (
            <div>
              <dt className="font-semibold text-navy">Source / agency</dt>
              <dd className="text-text-muted">{agency}</dd>
            </div>
          )}
          {extNo && (
            <div>
              <dt className="font-semibold text-navy">External case / reference #</dt>
              <dd className="text-text-muted">{extNo}</dd>
            </div>
          )}
          {checked && (
            <div>
              <dt className="font-semibold text-navy">Source last checked</dt>
              <dd className="text-text-muted">{checked}</dd>
            </div>
          )}
          {url && (
            <div>
              <dt className="font-semibold text-navy">Original listing</dt>
              <dd>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-all font-semibold text-navy underline underline-offset-2"
                >
                  Open original listing
                </a>
              </dd>
            </div>
          )}
        </dl>
      )}
    </section>
  )
}
