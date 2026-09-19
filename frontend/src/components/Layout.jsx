/**
 * Shared chrome: sticky navy header + gold Report CTA + hamburger.
 */
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'

const links = [
  { to: '/', label: 'Cases', end: true },
  { to: '/lookup', label: 'Lookup' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function Layout() {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-cream">
      <header className="sticky top-0 z-40 border-b border-navy-dark/40 bg-navy/95 text-white backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <Link
            to="/"
            className="group flex items-baseline gap-2"
            onClick={() => setOpen(false)}
          >
            <span className="font-display text-2xl tracking-tight text-white transition-colors group-hover:text-accent sm:text-3xl">
              FindMyPal
            </span>
            <span className="hidden text-[11px] font-semibold uppercase tracking-[0.18em] text-white/45 sm:inline">
              Missing persons
            </span>
          </Link>

          <nav className="hidden items-center gap-7 md:flex">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'nav-link-active' : ''}`
                }
              >
                {l.label}
              </NavLink>
            ))}
            <NavLink to="/report" className="btn-gold !px-4 !py-2 text-xs uppercase tracking-wide">
              Report
            </NavLink>
          </nav>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/20 transition-colors hover:bg-white/10 md:hidden"
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
          <nav className="border-t border-white/10 px-4 py-3 md:hidden">
            <ul className="flex flex-col gap-1">
              {[...links, { to: '/report', label: 'Report' }].map((l) => (
                <li key={l.to}>
                  <NavLink
                    to={l.to}
                    end={l.end}
                    className={({ isActive }) =>
                      `block rounded-md px-3 py-3 text-sm font-semibold transition-colors ${
                        isActive ? 'bg-white/10 text-white' : 'text-white/75 hover:bg-white/5'
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

      <main className="w-full flex-1">
        <Outlet />
      </main>

      <footer className="mt-auto border-t border-border bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-5 text-sm text-text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="font-display text-base text-navy">FindMyPal</span>
          <span>
            Community tips for missing persons. Always contact local authorities in an emergency.
          </span>
        </div>
      </footer>
    </div>
  )
}
