/**
 * Leaflet map: last known (red), tips (blue), chronological path.
 * Uses Esri public tiles (no API key).
 */
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import { geocode } from './DensityHeatMap.jsx'
import { BASEMAP_ATTR, BASEMAP_URL } from '../mapTiles.js'

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

export default function SightingsMap({ lastSeenLocation, sightings, showPath = true }) {
  const [lastKnown, setLastKnown] = useState(null)
  const [geoError, setGeoError] = useState('')

  useEffect(() => {
    let cancelled = false
    setGeoError('')
    geocode(lastSeenLocation)
      .then((coords) => {
        if (cancelled) return
        if (coords) setLastKnown([coords.lat, coords.lng])
        else setGeoError('Could not place last-known location on the map.')
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

  const center = allPositions[0] || [38.8691, -77.054]

  if (!allPositions.length) {
    return (
      <div className="space-y-2">
        <div className="flex h-72 items-center justify-center border border-navy/15 bg-navy-50 text-sm text-navy/55 sm:h-96">
          No tip coordinates yet{geoError ? ` · ${geoError}` : ''}. Submit a tip to place markers here.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="h-72 w-full overflow-hidden border border-navy/15 bg-navy-50 sm:h-96">
        <MapContainer
          center={center}
          zoom={12}
          scrollWheelZoom
          className="h-full w-full"
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer attribution={BASEMAP_ATTR} url={BASEMAP_URL} />
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
        Red = last known · Blue = tips · Dotted line = chronological path
        {geoError ? ` · ${geoError}` : ''}
      </p>
    </div>
  )
}
