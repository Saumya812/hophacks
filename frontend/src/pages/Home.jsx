/**
 * Landing — calm calligraphy + interactive wall gallery.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPersons } from '../api.js'
import WallGallery from '../components/WallGallery.jsx'
import Modal from '../components/Modal.jsx'

export default function Home() {
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await listPersons({ status: 'active' })
        if (cancelled) return
        setPersons(data.persons || [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Could not load cases')
          setPersons([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

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

        <div className="fade-up mt-12 w-full sm:mt-16" style={{ animationDelay: '120ms' }}>
          <WallGallery
            persons={persons}
            onSelect={(payload) => setSelected(payload)}
          />
        </div>

        <p className="mt-5 text-xs text-text-muted">
          {loading
            ? 'Loading active cases…'
            : persons.some((p) => p.photo_url)
              ? 'Hover a frame · click to tip, share, or look up'
              : persons.length > 0
                ? 'Active cases are listed under Missing — photos appear on the wall when available'
                : 'Active cases appear here when published'}
        </p>

        {error && (
          <p className="mt-2 max-w-md text-xs text-text-muted">
            Cases couldn&apos;t load ({error}).
          </p>
        )}

        <div
          className="fade-up mt-10 flex flex-wrap items-center justify-center gap-3"
          style={{ animationDelay: '220ms' }}
        >
          <Link to="/lookup" className="btn-primary">
            Search Lookup
          </Link>
          <Link to="/report" className="btn-secondary">
            Report
          </Link>
        </div>
      </section>

      <Modal
        open={Boolean(selected)}
        person={selected?.person || null}
        gallerySrc={selected?.gallerySrc || null}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
