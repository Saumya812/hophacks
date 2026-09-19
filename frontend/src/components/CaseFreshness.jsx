/**
 * Neutral freshness timestamps — never invent verification from page visits.
 */
import { formatEventDate, formatEventDateTime } from '../lib/caseHelpers.js'

function maxIso(times) {
  if (!times.length) return null
  return new Date(Math.max(...times)).toISOString()
}

export default function CaseFreshness({ person, sightings = [], updates = [] }) {
  const sourceChecked = formatEventDate(person?.source_last_checked_at)

  const tipTimes = (sightings || [])
    .map((s) => s.created_at || s.date_time)
    .filter(Boolean)
    .map((t) => new Date(t).getTime())
    .filter((n) => !Number.isNaN(n))
  const updateTimes = (updates || [])
    .map((u) => u.created_at)
    .filter(Boolean)
    .map((t) => new Date(t).getTime())
    .filter((n) => !Number.isNaN(n))

  const communityMs = [...tipTimes, ...updateTimes]
  const latestCommunity = communityMs.length
    ? formatEventDateTime(maxIso(communityMs))
    : null

  // Activity only — do not treat police-verification renewal as "source checked"
  const caseUpdatedCandidates = [
    person?.found_at,
    person?.ai_summary_updated_at,
    tipTimes.length ? maxIso(tipTimes) : null,
    updateTimes.length ? maxIso(updateTimes) : null,
  ].filter(Boolean)
  const caseUpdatedMs = caseUpdatedCandidates
    .map((t) => new Date(t).getTime())
    .filter((n) => !Number.isNaN(n))
  const caseUpdated =
    caseUpdatedMs.length > 0
      ? formatEventDateTime(new Date(Math.max(...caseUpdatedMs)).toISOString())
      : person?.created_at
        ? formatEventDateTime(person.created_at)
        : null

  return (
    <section className="surface-card p-4 sm:p-5">
      <h2 className="font-display text-lg text-navy">Case freshness</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Source last checked
          </dt>
          <dd className="text-text-primary">{sourceChecked || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Latest community tip / update
          </dt>
          <dd className="text-text-primary">{latestCommunity || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Case last updated
          </dt>
          <dd className="text-text-primary">{caseUpdated || 'Unknown'}</dd>
        </div>
      </dl>
      <p className="mt-2 text-xs text-text-muted">
        These are activity timestamps, not a verification badge. Opening this page does not mark the
        original source as checked.
      </p>
    </section>
  )
}
