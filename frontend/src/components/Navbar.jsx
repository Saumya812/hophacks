/**
 * Soft minimal navbar for calm landing aesthetic.
 */
import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/lookup', label: 'Lookup' },
  { to: '/report-missing', label: 'Missing' },
  { to: '/found', label: 'Found' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <header className="fixed left-0 right-0 top-0 z-50 border-b border-border/80 bg-cream/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1100px] items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-baseline gap-2" onClick={() => setOpen(false)}>
          <span className="font-display text-[22px] font-semibold leading-none text-ink">
            FindMyPal
          </span>
          <span
            className="hidden text-[10px] font-medium uppercase text-sage sm:inline"
            style={{ letterSpacing: '2px' }}
          >
            Missing Persons
          </span>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border text-ink transition-colors hover:bg-stone md:hidden"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" />
            </svg>
          )}
        </button>
      </div>

      {open && (
        <nav className="border-t border-border bg-cream md:hidden">
          <ul className="flex flex-col">
            {LINKS.map((l) => (
              <li key={l.to}>
                <NavLink
                  to={l.to}
                  end={l.end}
                  className={({ isActive }) =>
                    `flex h-14 items-center px-4 text-sm font-medium uppercase tracking-wide transition-colors ${
                      isActive ? 'bg-stone text-ink' : 'text-text-muted hover:bg-stone/60'
                    }`
                  }
                  onClick={() => setOpen(false)}
                >
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  )
}
