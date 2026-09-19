/**
 * Leaflet map: last known (red), sightings (blue), optional movement path + heat radii.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Circle,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'

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

async function geocode(query) {
  if (!query) return null
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) return null
  const data = await res.json()
  if (!data?.length) return null
  return [parseFloat(data[0].lat), parseFloat(data[0].lon)]
}

/** Count how many other tips fall within ~1.5km for heat intensity */
function heatWeight(sightings, s) {
  let n = 0
  for (const o of sightings) {
    if (o.id === s.id) continue
    const dlat = (o.location_lat - s.location_lat) * 111
    const dlng = (o.location_lng - s.location_lng) * 85
    if (Math.hypot(dlat, dlng) <= 1.5) n += 1
  }
  return n
}

export default function SightingsMap({ lastSeenLocation, sightings, showPath = true }) {
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

  const chronological = useMemo(() => {
    return [...(sightings || [])]
      .filter((s) => s.location_lat != null && s.location_lng != null)
      .sort((a, b) => new Date(a.date_time) - new Date(b.date_time))
  }, [sightings])

  const pathPositions = useMemo(
    () => chronological.map((s) => [s.location_lat, s.location_lng]),
    [chronological],
  )

  const allPositions = useMemo(() => {
    const pts = [...pathPositions]
    if (lastKnown) pts.push(lastKnown)
    return pts
  }, [pathPositions, lastKnown])

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

          {chronological.map((s) => {
            const heat = heatWeight(chronological, s)
            return (
              <Circle
                key={`heat-${s.id}`}
                center={[s.location_lat, s.location_lng]}
                radius={400 + heat * 350}
                pathOptions={{
                  color: '#1a2b4a',
                  fillColor: '#1a2b4a',
                  fillOpacity: Math.min(0.15 + heat * 0.12, 0.55),
                  weight: 1,
                }}
              />
            )
          })}

          {showPath && pathPositions.length >= 2 && (
            <Polyline
              positions={pathPositions}
              pathOptions={{
                color: '#1a2b4a',
                dashArray: '8 10',
                weight: 3,
                opacity: 0.85,
              }}
            />
          )}

          {chronological.map((s) => (
            <Marker key={s.id} position={[s.location_lat, s.location_lng]} icon={blueIcon}>
              <Popup>
                <strong>Sighting</strong>
                <br />
                {new Date(s.date_time).toLocaleString()}
                <br />
                Reporter confidence: {s.confidence_level}/5
                {s.credibility_score != null && (
                  <>
                    <br />
                    Credibility: {s.credibility_score}/10
                  </>
                )}
                <br />
                {s.description}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
      <p className="text-xs text-navy/55">
        Red = last known · Blue = tips · Circles = local heat · Dotted line = chronological path
        {geoError ? ` · ${geoError}` : ''}
      </p>
    </div>
  )
}
