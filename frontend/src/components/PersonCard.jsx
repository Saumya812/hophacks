/**
 * Compact person row used on the homepage case list.
 */
import { Link } from 'react-router-dom'

export default function PersonCard({ person }) {
  return (
    <Link
      to={`/person/${person.id}`}
      className="group block border-b border-navy/10 transition-colors last:border-b-0 hover:bg-navy-50/80"
    >
      <div className="flex gap-4 px-4 py-5 sm:gap-5 sm:px-5">
        <div className="relative h-24 w-20 shrink-0 overflow-hidden bg-navy-100 ring-1 ring-navy/10 sm:h-28 sm:w-24">
          {person.photo_url ? (
            <img
              src={person.photo_url}
              alt={person.name}
              className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
            />
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-1 bg-gradient-to-b from-navy-100 to-navy-200/80 px-1 text-center">
              <span className="font-display text-lg text-navy/35">
                {(person.name || '?').charAt(0)}
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-navy/35">
                No photo
              </span>
            </div>
          )}
          <span className="absolute left-0 top-0 bg-navy px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white">
            Active
          </span>
        </div>

        <div className="min-w-0 flex-1 self-center">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="font-display text-xl text-navy transition-colors group-hover:text-navy-900 sm:text-2xl">
              {person.name}
            </h2>
            <span className="text-sm text-navy/55">
              Age {person.age}
              {person.gender ? ` · ${person.gender}` : ''}
            </span>
          </div>
          <p className="mt-1.5 text-sm font-medium text-navy/65">
            Last seen · {person.last_seen_location}
            {person.last_seen_date ? ` · ${person.last_seen_date}` : ''}
          </p>
          <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-navy/75">
            {person.description}
          </p>
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.14em] text-navy/40 transition-colors group-hover:text-navy/70">
            View case →
          </p>
        </div>
      </div>
    </Link>
  )
}
