/**
 * Case card for the homepage grid.
 */
import { Link } from 'react-router-dom'

export default function PersonCard({ person, index = 0 }) {
  const lastSeen = [person.last_seen_location, person.last_seen_date]
    .filter(Boolean)
    .join(' · ')

  return (
    <Link
      to={`/person/${person.id}`}
      className="card-interactive group flex gap-4 p-4 fade-up"
      style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
    >
      <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-navy-100">
        {person.photo_url ? (
          <img
            src={person.photo_url}
            alt={person.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-display text-xl text-navy/30">
            {(person.name || '?').charAt(0)}
          </div>
        )}
        {(person.status || 'active').toLowerCase() === 'active' ? (
          <span className="absolute left-1.5 top-1.5 inline-flex items-center gap-1 rounded bg-white/95 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-success shadow-sm">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-success" />
            Active
          </span>
        ) : (person.status || '').toLowerCase() === 'found' ? (
          <span className="absolute left-1.5 top-1.5 rounded bg-white/95 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800 shadow-sm">
            Found
          </span>
        ) : null}
      </div>

      <div className="relative min-w-0 flex-1">
        <h2 className="font-display text-xl text-navy transition-colors group-hover:text-accent">
          {person.name}
        </h2>
        <p className="mt-1 text-[13px] font-medium text-accent">
          Last seen · {lastSeen || 'Unknown'}
        </p>
        <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-text-muted">
          {person.description}
        </p>
        <p className="mt-3 text-right text-sm font-semibold text-navy transition-transform group-hover:translate-x-0.5">
          View case
          <span className="inline-block transition-transform group-hover:translate-x-1"> →</span>
        </p>
      </div>
    </Link>
  )
}
