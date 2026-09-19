/**
 * Lookup report location heatmap.
 * Uses pre-geocoded `locations` from the API when present; otherwise geocodes
 * location strings from extracted sightings via /geo/search (same path as Cases).
 */
import { useEffect, useMemo, useState } from 'react'
import DensityHeatMap from './DensityHeatMap.jsx'
import { API_BASE } from '../api.js'

async function geocodeLabel(label) {
  const q = (label || '').trim()
  if (q.length < 2) return null
  try {
    const res = await fetch(`${API_BASE}/geo/search?q=${encodeURIComponent(q)}`)
    if (!res.ok) return null
    const data = await res.json()
    if (!data?.found) return null
    return {
      lat: Number(data.lat),
      lng: Number(data.lng),
      label: q,
      weight: 1,
    }
  } catch {
    return null
  }
}

export default function LookupLocationHeatmap({ locations = [], sightings = [], rawMentions = [] }) {
  const [resolved, setResolved] = useState([])
  const [status, setStatus] = useState('')

  const seedPoints = useMemo(() => {
    return (locations || [])
      .map((p) => ({
        lat: Number(p.lat),
        lng: Number(p.lng),
        weight: Number(p.count ?? p.weight ?? 1) || 1,
        label: p.label || 'Mentioned place',
      }))
      .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
  }, [locations])

  const labelsToGeocode = useMemo(() => {
    if (seedPoints.length) return []
    const counts = new Map()
    const add = (loc) => {
      const t = (loc || '').trim()
      if (!t || /^(unknown|n\/a|none|null)$/i.test(t)) return
      // Drop leading prepositions left by heuristic extractors
      const cleaned = t.replace(/^(in|near|around|at|from)\s+/i, '').trim()
      if (cleaned.length < 2) return
      counts.set(cleaned, (counts.get(cleaned) || 0) + 1)
    }
    for (const s of sightings || []) add(s.location)
    // Also scrape location phrases from raw mention text when sightings lack coords
    if (!counts.size) {
      const re = /\b(?:in|near|around|at)\s+([A-Z][A-Za-z0-9 .'-]{2,48})/g
      for (const m of rawMentions || []) {
        const blob = `${m.title || ''} ${m.text || m.snippet || ''}`
        let match
        while ((match = re.exec(blob))) add(match[1])
      }
    }
    return [...counts.entries()].slice(0, 12)
  }, [seedPoints.length, sightings, rawMentions])

  useEffect(() => {
    let cancelled = false
    if (seedPoints.length) {
      setResolved(seedPoints)
      setStatus('')
      return undefined
    }
    if (!labelsToGeocode.length) {
      setResolved([])
      setStatus('No location strings found in this report to plot.')
      return undefined
    }

    setStatus('Geocoding mentioned places…')
    ;(async () => {
      const out = []
      for (const [label, count] of labelsToGeocode) {
        if (cancelled) return
        const hit = await geocodeLabel(label)
        if (hit) out.push({ ...hit, weight: count })
      }
      if (cancelled) return
      setResolved(out)
      setStatus(
        out.length
          ? ''
          : 'Could not geocode mentioned places. Try a name with city/region in public posts.',
      )
    })()

    return () => {
      cancelled = true
    }
  }, [seedPoints, labelsToGeocode])

  return (
    <section className="space-y-3">
      <div className="border-b border-navy/15 pb-2">
        <h3 className="font-display text-2xl text-navy">Location heatmap</h3>
        <p className="text-sm text-navy/55">
          Density from geocoded public-web mention places (same map stack as Cases).
        </p>
      </div>
      {status ? <p className="text-sm text-navy/55">{status}</p> : null}
      <DensityHeatMap
        key={`lookup-heat-${resolved.length}-${resolved[0]?.lat ?? 'x'}`}
        points={resolved}
        title="Lookup location heatmap"
      />
    </section>
  )
}
