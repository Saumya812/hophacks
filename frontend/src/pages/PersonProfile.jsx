/**
 * Person profile page — details, timeline, sightings map, flyer PDF.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPerson, listSightings } from '../api.js'
import SightingsMap from '../components/SightingsMap.jsx'
import FlyerButton from '../components/FlyerButton.jsx'

export default function PersonProfile() {
  const { id } = useParams()
  const [person, setPerson] = useState(null)
  const [sightings, setSightings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [p, s] = await Promise.all([getPerson(id), listSightings(id)])
        if (cancelled) return
        setPerson(p)
        setSightings(s.sightings || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [id])

  if (loading) return <p className="text-navy/60">Loading profile…</p>
  if (error) {
    return (
      <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
    )
  }
  if (!person) return null

  // Timeline: last-seen event + sightings newest-first already from API
  const timeline = [
    {
      id: 'last-seen',
      label: 'Last known',
      when: person.last_seen_date,
      text: person.last_seen_location,
      kind: 'last',
    },
    ...sightings.map((s) => ({
      id: s.id,
      label: `Sighting (confidence ${s.confidence_level}/5)`,
      when: s.date_time,
      text: s.description,
      kind: 'sighting',
    })),
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-6 sm:flex-row">
        <div className="h-56 w-full shrink-0 overflow-hidden bg-navy-100 sm:h-64 sm:w-52">
          {person.photo_url ? (
            <img
              src={person.photo_url}
              alt={person.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-sm text-navy/40">
              No photo
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-navy/50">
              {person.status} case
            </p>
            <h1 className="font-display text-3xl text-navy sm:text-4xl">{person.name}</h1>
            <p className="mt-1 text-navy/70">
              Age {person.age}
              {person.gender ? ` · ${person.gender}` : ''}
            </p>
          </div>

          <p className="text-navy/85">{person.description}</p>

          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold text-navy">Last seen location</dt>
              <dd className="text-navy/75">{person.last_seen_location}</dd>
            </div>
            <div>
              <dt className="font-semibold text-navy">Last seen date</dt>
              <dd className="text-navy/75">{person.last_seen_date}</dd>
            </div>
            {person.police_report_number && (
              <div>
                <dt className="font-semibold text-navy">Police report #</dt>
                <dd className="text-navy/75">{person.police_report_number}</dd>
              </div>
            )}
          </dl>

          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={`/tip/${person.id}`} className="btn-primary">
              Submit a tip
            </Link>
            <FlyerButton person={person} />
          </div>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-navy">Sightings map</h2>
        <SightingsMap
          lastSeenLocation={person.last_seen_location}
          sightings={sightings}
        />
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-navy">Timeline</h2>
        {timeline.length === 0 ? (
          <p className="text-navy/60">No events yet.</p>
        ) : (
          <ol className="space-y-0 border-l-2 border-navy/20 pl-4">
            {timeline.map((item) => (
              <li key={item.id} className="relative pb-5">
                <span
                  className={`absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full ${
                    item.kind === 'last' ? 'bg-red-600' : 'bg-blue-600'
                  }`}
                />
                <p className="text-xs font-semibold uppercase tracking-wide text-navy/50">
                  {item.label}
                </p>
                <p className="text-sm text-navy/55">
                  {item.when ? new Date(item.when).toLocaleString() : '—'}
                </p>
                <p className="mt-1 text-navy/85">{item.text}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}
