/**
 * Save / unsave a case on this device (localStorage).
 */
import { useCaseSaved } from '../hooks/useSavedCases.js'

export default function SaveCaseButton({ personId, className = '', compact = false }) {
  const { saved, toggle } = useCaseSaved(personId)

  return (
    <button
      type="button"
      className={
        className ||
        (compact
          ? 'rounded border border-navy/20 bg-cream px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-navy hover:border-gold/50'
          : 'btn-secondary')
      }
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggle()
      }}
      aria-pressed={saved}
      title={saved ? 'Remove from saved on this device' : 'Save on this device'}
    >
      {saved ? (compact ? 'Saved' : 'Saved on this device') : compact ? 'Save' : 'Save on this device'}
    </button>
  )
}
