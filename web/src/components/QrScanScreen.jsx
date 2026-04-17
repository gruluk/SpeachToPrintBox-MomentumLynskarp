import { useEffect, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'

function extractUserId(text) {
  // Match URLs like https://lynskarp.soprasteria.no/u/{uuid}
  const match = text.match(/\/u\/([0-9a-f-]{36})/)
  if (match) return match[1]
  // Also accept raw UUIDs
  const uuidMatch = text.match(/^[0-9a-f-]{36}$/)
  return uuidMatch ? uuidMatch[0] : null
}

export default function QrScanScreen({ onScanned, onCancel }) {
  const scannerRef = useRef(null)
  const busyRef = useRef(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const scanner = new Html5Qrcode('qr-reader')
    scannerRef.current = scanner

    scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 350, height: 150 } },
      async (decodedText) => {
        if (busyRef.current) return
        const userId = extractUserId(decodedText)
        if (!userId) return

        busyRef.current = true
        setError('')
        try {
          scanner.pause()
        } catch {}

        try {
          const res = await fetch(`/users/${userId}`)
          if (!res.ok) {
            setError('Bruker ikke funnet. Prøv igjen.')
            busyRef.current = false
            try { scanner.resume() } catch {}
            return
          }
          const user = await res.json()
          onScanned(user)
        } catch {
          setError('Noe gikk galt. Prøv igjen.')
          busyRef.current = false
          try { scanner.resume() } catch {}
        }
      },
    ).catch(() => {
      setError('Kunne ikke starte kameraet.')
    })

    return () => {
      scanner.stop().catch(() => {})
    }
  }, [])

  return (
    <div className="screen center">
      <h2>Skann QR-koden din</h2>
      <p className="status-sub">Hold klistrelappen opp mot kameraet</p>
      <div className="qr-scanner-wrap">
        <div id="qr-reader" />
      </div>
      {error && <p className="qr-scan-error">{error}</p>}
      <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
    </div>
  )
}
