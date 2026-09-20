/**
 * Soft minimal footer.
 */
import { Link } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Home' },
  { to: '/lookup', label: 'Lookup' },
  { to: '/report-missing', label: 'Missing' },
  { to: '/found', label: 'Found' },
  { to: '/report', label: 'Report' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-border bg-stone/60">
      <div className="mx-auto grid max-w-[1100px] gap-10 px-4 py-12 sm:grid-cols-2 sm:px-6">
        <div>
          <p className="font-display text-2xl font-semibold text-ink">FindMyPal</p>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-text-muted">
            Someone needs you to look.
          </p>
        </div>
        <div className="sm:justify-self-end">
          <p
            className="mb-3 text-[10px] font-medium uppercase text-sage"
            style={{ letterSpacing: '2px' }}
          >
            Navigate
          </p>
          <ul className="flex flex-col gap-2 text-sm text-text-muted">
            {LINKS.map((l) => (
              <li key={l.to}>
                <Link to={l.to} className="transition-colors hover:text-ink">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-border px-4 py-5 sm:px-6">
        <p className="mx-auto max-w-3xl text-center text-[11px] leading-relaxed text-text-muted">
          FindMyPal is a community tip-sharing platform and is not affiliated with law enforcement
          or official databases. Misuse of this platform — including false reports, harassment, or
          impersonation — may result in account removal and strict legal action.
        </p>
      </div>
    </footer>
  )
}
