/**
 * Generates a downloadable missing-person flyer PDF with:
 * photo, name, description, and a QR code linking to the profile URL.
 */
import { useState } from 'react'
import { jsPDF } from 'jspdf'
import QRCode from 'qrcode'

async function loadImageAsDataUrl(url) {
  if (!url) return null
  try {
    const res = await fetch(url, { mode: 'cors' })
    if (!res.ok) return null
    const blob = await res.blob()
    return await new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

export default function FlyerButton({ person }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleGenerate() {
    setBusy(true)
    setError('')
    try {
      const profileUrl = `${window.location.origin}/person/${person.id}`
      const qrDataUrl = await QRCode.toDataURL(profileUrl, {
        width: 256,
        margin: 1,
        color: { dark: '#1a2b4a', light: '#ffffff' },
      })

      const photoDataUrl = await loadImageAsDataUrl(person.photo_url)

      const doc = new jsPDF({ unit: 'pt', format: 'letter' })
      const pageW = doc.internal.pageSize.getWidth()
      const margin = 48

      // Navy header bar
      doc.setFillColor(26, 43, 74)
      doc.rect(0, 0, pageW, 72, 'F')
      doc.setTextColor(255, 255, 255)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(22)
      doc.text('MISSING PERSON', margin, 46)

      doc.setTextColor(26, 43, 74)
      doc.setFontSize(11)
      doc.setFont('helvetica', 'normal')
      doc.text('FindMyPal', pageW - margin, 46, { align: 'right' })

      let y = 110

      // Photo (or placeholder box)
      const photoW = 160
      const photoH = 200
      if (photoDataUrl) {
        const format = photoDataUrl.includes('image/png') ? 'PNG' : 'JPEG'
        doc.addImage(photoDataUrl, format, margin, y, photoW, photoH)
      } else {
        doc.setDrawColor(26, 43, 74)
        doc.setFillColor(242, 244, 247)
        doc.rect(margin, y, photoW, photoH, 'FD')
        doc.setFontSize(12)
        doc.text('No photo', margin + photoW / 2, y + photoH / 2, { align: 'center' })
      }

      // Details column
      const textX = margin + photoW + 28
      const textMaxW = pageW - textX - margin

      doc.setFont('helvetica', 'bold')
      doc.setFontSize(24)
      doc.text(person.name || 'Unknown', textX, y + 24)

      doc.setFont('helvetica', 'normal')
      doc.setFontSize(12)
      const meta = [
        `Age: ${person.age ?? '—'}`,
        person.gender ? `Gender: ${person.gender}` : null,
        `Last seen: ${person.last_seen_location || '—'}`,
        person.last_seen_date ? `Date: ${person.last_seen_date}` : null,
        person.police_report_number
          ? `Police report #: ${person.police_report_number}`
          : null,
      ].filter(Boolean)

      let metaY = y + 52
      meta.forEach((line) => {
        doc.text(line, textX, metaY)
        metaY += 18
      })

      metaY += 10
      doc.setFont('helvetica', 'bold')
      doc.text('Description', textX, metaY)
      metaY += 16
      doc.setFont('helvetica', 'normal')
      const descLines = doc.splitTextToSize(person.description || '', textMaxW)
      doc.text(descLines, textX, metaY)

      // QR + tip CTA at bottom
      const qrSize = 110
      const qrY = 640
      doc.addImage(qrDataUrl, 'PNG', margin, qrY, qrSize, qrSize)

      doc.setFont('helvetica', 'bold')
      doc.setFontSize(14)
      doc.text('Scan to view this case & submit a tip', margin + qrSize + 20, qrY + 36)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      doc.setTextColor(80, 90, 110)
      doc.text(profileUrl, margin + qrSize + 20, qrY + 56)
      doc.text(
        'If you have information, contact local authorities immediately.',
        margin + qrSize + 20,
        qrY + 74,
      )

      const safeName = (person.name || 'person').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '_')
      doc.save(`FindMyPal_Flyer_${safeName || 'case'}.pdf`)
    } catch (err) {
      setError(err.message || 'Failed to generate flyer')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <button type="button" className="btn-secondary" onClick={handleGenerate} disabled={busy}>
        {busy ? 'Generating flyer…' : 'Download flyer PDF'}
      </button>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
    </div>
  )
}
