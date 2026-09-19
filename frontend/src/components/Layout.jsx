/**
 * Shared chrome: refined navy header + footer.
 * Pages render inside <Outlet />.
 */
import { Link, NavLink, Outlet } from 'react-router-dom'

const navClass = ({ isActive }) =>
  [
    'relative text-sm font-semibold tracking-wide transition-colors',
    isActive ? 'text-white' : 'text-white/70 hover:text-white',
    isActive
      ? "after:absolute after:-bottom-1 after:left-0 after:h-px after:w-full after:bg-white/80 after:content-['']"
      : '',
  ].join(' ')

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="relative overflow-hidden border-b border-navy-900/50 bg-navy text-white">
        {/* Subtle depth in the header band */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              'radial-gradient(ellipse 60% 120% at 90% 50%, rgba(255,255,255,0.12), transparent 55%)',
          }}
        />
        <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 sm:py-5">
          <Link to="/" className="group flex items-baseline gap-2">
            <span className="font-display text-2xl tracking-tight text-white sm:text-3xl">
              FindMyPal
            </span>
            <span className="hidden text-[11px] font-semibold uppercase tracking-[0.18em] text-white/45 sm:inline">
              Missing persons
            </span>
          </Link>
          <nav className="flex items-center gap-4 sm:gap-7">
            <NavLink to="/" end className={navClass}>
              Cases
            </NavLink>
            <NavLink to="/lookup" className={navClass}>
              Lookup
            </NavLink>
            <NavLink to="/report" className={navClass}>
              Report
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>

      <footer className="mt-auto border-t border-navy/10 bg-white/80">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-5 text-sm text-navy/55 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="font-display text-base text-navy/70">FindMyPal</span>
          <span>Community tips for missing persons. Always contact local authorities in an emergency.</span>
        </div>
      </footer>
    </div>
  )
}
