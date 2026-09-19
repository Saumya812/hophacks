/**
 * Leaflet map: last known (red), tips (blue), chronological path.
 * Layer toggles + legend. Uses Esri public tiles (no API key).
 */
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap, LayersControl } from 'react-leaflet'
import L from 'leaflet'
import { geocode } from './DensityHeatMap.jsx'
import { BASEMAP_ATTR, BASEMAP_URL, SATELLITE_ATTR, SATELLITE_URL } from '../mapTiles.js'
import { formatEventDateTime, safeHttpUrl } from '../lib/caseHelpers.js'

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

export default function SightingsMap({
  lastSeenLocation,
  lastSeenDate,
  sourceListingUrl,
  sightings,
  showPath = true,
}) {
  const [lastKnown, setLastKnown] = useState(null)
  const [geoError, setGeoError] = useState('')
  const [showLastSeen, setShowLastSeen] = useState(true)
  const [showTips, setShowTips] = useState(true)
  const [showPathLine, setShowPathLine] = useState(showPath)
  const listingUrl = safeHttpUrl(sourceListingUrl)

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
    const pts = []
    if (showTips) pts.push(...pathPositions)
    if (showLastSeen && lastKnown) pts.push(lastKnown)
    if (!pts.length && lastKnown) pts.push(lastKnown)
    if (!pts.length) pts.push(...pathPositions)
    return pts
  }, [pathPositions, lastKnown, showLastSeen, showTips])

  const center = allPositions[0] || [38.8691, -77.054]

  if (!lastKnown && chronological.length === 0) {
    return (
      <div className="space-y-2">
        <div className="map-frame flex items-center justify-center bg-navy-50 text-sm text-text-muted">
          No tip coordinates yet{geoError ? ` · ${geoError}` : ''}. Submit a tip to place markers
          here. City-level last-seen places are approximate, not exact addresses.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-3 text-xs font-semibold text-navy">
        <label className="inline-flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            className="accent-navy"
            checked={showLastSeen}
            onChange={(e) => setShowLastSeen(e.target.checked)}
          />
          Last known (reported)
        </label>
        <label className="inline-flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            className="accent-navy"
            checked={showTips}
            onChange={(e) => setShowTips(e.target.checked)}
          />
          Community tips (unverified)
        </label>
        <label className="inline-flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            className="accent-navy"
            checked={showPathLine}
            onChange={(e) => setShowPathLine(e.target.checked)}
          />
          Tip path
        </label>
      </div>

      <div className="map-frame bg-navy-50">
        <MapContainer
          center={center}
          zoom={12}
          scrollWheelZoom
          className="h-full w-full"
          style={{ height: '100%', width: '100%' }}
        >
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="Streets">
              <TileLayer attribution={BASEMAP_ATTR} url={BASEMAP_URL} />
            </LayersControl.BaseLayer>
            <LayersControl.BaseLayer name="Satellite">
              <TileLayer attribution={SATELLITE_ATTR} url={SATELLITE_URL} />
            </LayersControl.BaseLayer>
          </LayersControl>
          <FitBounds positions={allPositions} />

          {showLastSeen && lastKnown && (
            <Marker position={lastKnown} icon={redIcon}>
              <Popup>
                <strong>Reported last known</strong>
                <br />
                {lastSeenLocation || 'Location on file'}
                <br />
                Event date: {formatEventDateTime(lastSeenDate) || 'Unknown'}
                <br />
                <em className="text-xs">Approximate geocode — not an exact address pin.</em>
                {listingUrl ? (
                  <>
                    <br />
                    <a href={listingUrl} target="_blank" rel="noopener noreferrer">
                      Original listing
                    </a>
                  </>
                ) : null}
              </Popup>
            </Marker>
          )}

          {showPathLine && showTips && pathPositions.length >= 2 && (
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

          {showTips &&
            chronological.map((s) => (
              <Marker key={s.id} position={[s.location_lat, s.location_lng]} icon={blueIcon}>
                <Popup>
                  <strong>Community tip (unverified)</strong>
                  <br />
                  Event date: {formatEventDateTime(s.date_time) || 'Unknown'}
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
      <div className="flex flex-wrap gap-3 text-xs text-navy/70">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-danger" /> Reported last known
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-navy" /> Community tips
          (unverified)
        </span>
        {geoError ? <span>· {geoError}</span> : null}
      </div>
    </div>
  )
}
