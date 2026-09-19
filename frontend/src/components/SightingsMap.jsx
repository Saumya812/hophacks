/**
 * Leaflet map for a person profile.
 * - Red marker: last known location (geocoded from text, or fallback)
 * - Blue markers: submitted sightings with timestamps
 */
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix default marker icons broken by Vite bundling
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const blueIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

/** Fit map bounds whenever marker set changes */
function FitBounds({ positions }) {
  const map = useMap()
  useEffect(() => {
    if (!positions.length) return
    if (positions.length === 1) {
      map.setView(positions[0], 13)
      return
    }
    map.fitBounds(positions, { padding: [40, 40] })
  }, [map, positions])
  return null
}

/** Geocode free-text last_seen_location via OpenStreetMap Nominatim */
async function geocode(query) {
  if (!query) return null
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`
  const res = await fetch(url, {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) return null
  const data = await res.json()
  if (!data?.length) return null
  return [parseFloat(data[0].lat), parseFloat(data[0].lon)]
}

export default function SightingsMap({ lastSeenLocation, sightings }) {
  const [lastKnown, setLastKnown] = useState(null)
  const [geoError, setGeoError] = useState('')

  useEffect(() => {
    let cancelled = false
    setGeoError('')
    geocode(lastSeenLocation)
      .then((coords) => {
        if (!cancelled) setLastKnown(coords)
      })
      .catch(() => {
        if (!cancelled) setGeoError('Could not place last-known location on the map.')
      })
    return () => {
      cancelled = true
    }
  }, [lastSeenLocation])

  const sightingPositions = useMemo(
    () =>
      (sightings || [])
        .filter((s) => s.location_lat != null && s.location_lng != null)
        .map((s) => [s.location_lat, s.location_lng]),
    [sightings],
  )

  const allPositions = useMemo(() => {
    const pts = [...sightingPositions]
    if (lastKnown) pts.push(lastKnown)
    return pts
  }, [sightingPositions, lastKnown])

  // Default center: Baltimore (project seed city) if nothing else is available
  const center = allPositions[0] || [39.2904, -76.6122]

  return (
    <div className="space-y-2">
      <div className="h-72 w-full overflow-hidden border border-navy/15 bg-navy-50 sm:h-96">
        <MapContainer center={center} zoom={12} scrollWheelZoom className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds positions={allPositions} />

          {lastKnown && (
            <Marker position={lastKnown} icon={redIcon}>
              <Popup>
                <strong>Last known location</strong>
                <br />
                {lastSeenLocation}
              </Popup>
            </Marker>
          )}

          {(sightings || []).map((s) => (
            <Marker
              key={s.id}
              position={[s.location_lat, s.location_lng]}
              icon={blueIcon}
            >
              <Popup>
                <strong>Sighting</strong>
                <br />
                {new Date(s.date_time).toLocaleString()}
                <br />
                Confidence: {s.confidence_level}/5
                <br />
                {s.description}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      <p className="text-xs text-navy/55">
        Red = last known location · Blue = reported sightings
        {geoError ? ` · ${geoError}` : ''}
      </p>
    </div>
  )
}
