/**
 * Lightweight toast — bottom-right. Use showToast(message, type).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

const ToastContext = createContext(null)

let externalShow = null

/** Imperative helper usable outside React trees */
export function showToast(message, type = 'info') {
  if (externalShow) externalShow(message, type)
}

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)

  const show = useCallback((message, type = 'info') => {
    setToast({ message, type, id: Date.now() })
  }, [])

  useEffect(() => {
    externalShow = show
    return () => {
      if (externalShow === show) externalShow = null
    }
  }, [show])

  useEffect(() => {
    if (!toast) return undefined
    const t = setTimeout(() => setToast(null), 4200)
    return () => clearTimeout(t)
  }, [toast])

  const value = useMemo(() => ({ showToast: show }), [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  return ctx?.showToast || showToast
}

export default function Toast({ message, type = 'info', onClose }) {
  const bg =
    type === 'success' ? '#16a34a' : type === 'warning' ? '#b45309' : '#1a2b4a'

  return (
    <div
      role="status"
      className="toast-slide-in"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        background: bg,
        color: 'white',
        padding: '12px 20px',
        borderRadius: '8px',
        fontFamily: 'Inter, system-ui, sans-serif',
        fontSize: '14px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        maxWidth: 'min(90vw, 360px)',
      }}
    >
      <span aria-hidden>{type === 'success' ? '✓' : 'ℹ'}</span>
      <span className="flex-1">{message}</span>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss"
          style={{
            background: 'transparent',
            border: 0,
            color: 'white',
            cursor: 'pointer',
            fontSize: '16px',
            lineHeight: 1,
            opacity: 0.8,
          }}
        >
          ×
        </button>
      )}
    </div>
  )
}
