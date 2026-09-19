/**
 * Landing — calm centered calligraphy + wall gallery.
 */
import { Link } from 'react-router-dom'
import WallGallery from '../components/WallGallery.jsx'

export default function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-cream">
      <section className="mx-auto flex max-w-[1100px] flex-col items-center px-4 pb-20 pt-14 text-center sm:px-6 sm:pt-20">
        <div className="fade-up max-w-2xl">
          <h1
            className="font-display font-normal text-ink"
            style={{
              fontSize: 'clamp(1.65rem, 4.2vw, 2.75rem)',
              lineHeight: 1.25,
              letterSpacing: '-0.01em',
            }}
          >
            There are{' '}
            <span className="italic text-sage">26,000+</span> active missing cases in the U.S.
          </h1>
          <p
            className="mt-5 font-display italic text-ink/80"
            style={{ fontSize: 'clamp(1.35rem, 3vw, 2rem)', lineHeight: 1.3 }}
          >
            Find your Pal.
          </p>
          <p
            className="mx-auto mt-5 max-w-md text-[15px] font-light leading-relaxed text-text-muted"
            style={{ letterSpacing: '0.01em' }}
          >
            Help families reconnect. Browse active cases, submit a tip, or search the public web
            for someone you&apos;re looking for.
          </p>
        </div>

        <div
          className="fade-up mt-12 w-full sm:mt-16"
          style={{ animationDelay: '120ms' }}
        >
          <WallGallery />
        </div>

        <div
          className="fade-up mt-12 flex flex-wrap items-center justify-center gap-3"
          style={{ animationDelay: '220ms' }}
        >
          <Link to="/lookup" className="btn-primary">
            Search Lookup
          </Link>
          <Link to="/report" className="btn-secondary">
            Report missing
          </Link>
        </div>

        <p className="mt-8 max-w-sm text-center text-xs text-text-muted/80">
          Drop photos into{' '}
          <code className="rounded bg-stone px-1.5 py-0.5 text-[11px]">public/gallery/</code>
          {' '}as <code className="rounded bg-stone px-1.5 py-0.5 text-[11px]">01.jpg</code>–
          <code className="rounded bg-stone px-1.5 py-0.5 text-[11px]">09.jpg</code>
        </p>
      </section>
    </div>
  )
}
