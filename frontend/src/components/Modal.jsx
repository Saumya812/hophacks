/**
 * Case preview modal — gallery click → Lookup / tip / share.
 */
import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { formatEventDate } from '../lib/caseHelpers.js'

export default function Modal({ person, open, onClose }) {
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return undefined
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open || !person) return null

  async function shareCase() {
    const url = `${window.location.origin}/person/${person.id}`
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${person.name} — FindMyPal`,
          text: `Help find ${person.name}`,
          url,
        })
      } else {
        await navigator.clipboard.writeText(url)
      }
    } catch {
      try {
        await navigator.clipboard.writeText(url)
      } catch {
        /* ignore */
      }
    }
  }

  return (
    <div
      className="modal-backdrop fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="case-modal-title"
      onClick={onClose}
    >
      <div
        className="modal-panel relative w-full max-w-[480px] overflow-hidden bg-white shadow-modal"
        style={{ borderRadius: 16 }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-navy transition-colors hover:bg-misty"
          aria-label="Close"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.5" />
          </svg>
        </button>

        <div className="relative">
          {person.photo_url ? (
            <img
              src={person.photo_url}
              alt={person.name}
              className="h-[280px] w-full object-cover"
              style={{ borderRadius: '16px 16px 0 0' }}
            />
          ) : (
            <div
              className="flex h-[280px] w-full items-center justify-center bg-navy font-display text-5xl text-white/30"
              style={{ borderRadius: '16px 16px 0 0' }}
            >
              {(person.name || '?').charAt(0)}
            </div>
          )}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-navy to-transparent px-5 pb-4 pt-16">
            <p
              className="text-[11px] font-semibold uppercase text-gold"
              style={{ letterSpacing: '2px' }}
            >
              Active case
            </p>
          </div>
        </div>

        <div className="p-6">
          <h2 id="case-modal-title" className="font-display text-[28px] text-navy">
            {person.name}
          </h2>
          <p className="mt-1 text-sm text-text-muted">
            Age {person.age}
            {person.gender ? ` · ${person.gender}` : ''}
          </p>
          <p className="mt-3 flex items-start gap-2 text-[13px] text-navy">
            <span className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full bg-gold" />
            <span>
              {person.last_seen_location}
              {person.last_seen_date
                ? ` · ${formatEventDate(person.last_seen_date) || person.last_seen_date}`
                : ''}
            </span>
          </p>
          {person.description && (
            <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-text-primary">
              {person.description}
            </p>
          )}

          <div className="my-4 h-px bg-border" />

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              className="btn-gold flex-1 !px-3 !py-3 text-xs sm:text-sm"
              onClick={() => {
                onClose()
                navigate('/lookup')
              }}
            >
              Search on Lookup →
            </button>
            <Link
              to={`/tip/${person.id}`}
              className="btn-primary flex-1 !px-3 !py-3 text-center text-xs sm:text-sm"
              onClick={onClose}
            >
              Submit a tip
            </Link>
            <button
              type="button"
              className="btn-secondary flex-1 !px-3 !py-3 text-xs sm:text-sm"
              onClick={shareCase}
            >
              Share case
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
