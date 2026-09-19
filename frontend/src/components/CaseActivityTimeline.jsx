/**
 * Vertical case activity timeline (tips, created, police, found).
 */
import { formatEventDateTime } from '../lib/caseHelpers.js'

const DOT = {
  case_created: 'bg-navy',
  tip_submitted: 'bg-[#a8906e]',
  police_notified: 'bg-[#c5cfc5]',
  verified_found: 'bg-emerald-600',
}

export default function CaseActivityTimeline({ person, tips = [] }) {
  const events = []

  if (person?.created_at) {
    events.push({
      type: 'case_created',
      timestamp: person.created_at,
      content: `Case opened for ${person.name}`,
      author: 'system',
    })
  }

  for (const t of tips) {
    const when = t.created_at || t.date_time
    events.push({
      type: 'tip_submitted',
      timestamp: when,
      content: t.description || 'Community tip submitted',
      author: 'public',
      id: t.id,
    })
    // Only show police step when EmailJS (or similar) actually reported success
    if (t.police_notified === true) {
      events.push({
        type: 'police_notified',
        timestamp: when,
        content: 'Local authorities were notified about this tip',
        author: 'system',
        id: `pd-${t.id}`,
      })
    }
  }

  if ((person?.status || '').toLowerCase() === 'found') {
    events.push({
      type: 'verified_found',
      timestamp: person.found_date || person.found_at || person.last_verified_at,
      content: person.found_notes || person.found_message || 'Marked found / verified by authorities',
      author: person.verified_by === 'law_enforcement' ? 'police' : 'system',
    })
  }

  events.sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))

  if (events.length === 0) {
    return (
      <p className="text-sm text-text-muted">No activity yet. Tips will appear here in real time.</p>
    )
  }

  return (
    <ol className="relative ml-2 border-l-2 border-[#e5e7eb] pl-0">
      {events.map((ev, i) => (
        <li key={ev.id || `${ev.type}-${i}`} className="relative mb-4 ml-5">
          <span
            className={`absolute -left-[29px] top-4 h-3 w-3 rounded-full border-2 border-white ${
              DOT[ev.type] || 'bg-navy'
            }`}
            aria-hidden
          />
          <div className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-border/60">
            <p className="text-[11px] font-bold uppercase tracking-wide text-text-muted">
              {labelFor(ev.type)} · {ev.author}
            </p>
            <p className="mt-1 text-sm text-ink">{ev.content}</p>
            <p className="mt-2 text-xs text-text-muted">
              {formatEventDateTime(ev.timestamp) || 'Unknown time'}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function labelFor(type) {
  switch (type) {
    case 'case_created':
      return 'Case created'
    case 'tip_submitted':
      return 'Tip submitted'
    case 'police_notified':
      return 'Police notified'
    case 'verified_found':
      return 'Verified found'
    default:
      return type
  }
}
