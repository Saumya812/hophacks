/**
 * Full-screen celebration when a case is verified found by authorities.
 */
import { Link } from 'react-router-dom'

export default function FoundOverlay({ personName, onClose }) {
  const name = personName || 'This person'

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center px-4"
      style={{ background: 'rgba(26, 43, 74, 0.95)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="found-overlay-title"
    >
      <div className="found-confetti" aria-hidden>
        {Array.from({ length: 20 }).map((_, i) => (
          <span key={i} className={`found-confetti-piece piece-${i % 5}`} />
        ))}
      </div>

      <div className="relative z-10 max-w-lg text-center text-white">
        <svg
          className="mx-auto mb-6 h-16 w-16 text-emerald-400 found-check-draw"
          viewBox="0 0 52 52"
          fill="none"
          aria-hidden
        >
          <circle cx="26" cy="26" r="24" stroke="currentColor" strokeWidth="2" opacity="0.35" />
          <path
            className="found-check-path"
            d="M14 27 l8 8 l16 -18"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        </svg>

        <h2
          id="found-overlay-title"
          className="font-display text-white"
          style={{ fontSize: 'clamp(1.75rem, 4vw, 2.25rem)', lineHeight: 1.2 }}
        >
          {name} has been found safe
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-white/80" style={{ fontFamily: 'Inter, system-ui' }}>
          This case has been verified by authorities and is now closed. Thank you to everyone who
          submitted tips.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link to="/found" className="btn-gold" onClick={onClose}>
            View resolved case →
          </Link>
          <button type="button" className="btn-outline-white !text-white !border-white/40" onClick={onClose}>
            Stay on profile
          </button>
        </div>
      </div>
    </div>
  )
}
