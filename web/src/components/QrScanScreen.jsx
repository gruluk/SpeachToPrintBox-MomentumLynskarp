import { useEffect, useRef, useState, useCallback } from 'react'
import jsQR from 'jsqr'

const ZOOM = 2.5
const SCAN_INTERVAL = 150 // ms between scans

export default function QrScanScreen({ onScanned, onCancel }) {
  const videoRef = useRef(null)
  const bgCanvasRef = useRef(null)
  const zoomCanvasRef = useRef(null)
  const busyRef = useRef(false)
  const rafRef = useRef(null)
  const scanTimerRef = useRef(null)
  const streamRef = useRef(null)
  const [error, setError] = useState('')
  const [scanning, setScanning] = useState(true)

  const handleCode = useCallback(async (code) => {
    if (busyRef.current || !code) return
    busyRef.current = true
    setError('')

    try {
      const res = await fetch(`/users/by-code/${encodeURIComponent(code)}`)
      if (!res.ok) {
        setError('Bruker ikke funnet. Prøv igjen.')
        busyRef.current = false
        return
      }
      const user = await res.json()
      setScanning(false)
      onScanned(user)
    } catch {
      setError('Noe gikk galt. Prøv igjen.')
      busyRef.current = false
    }
  }, [onScanned])

  useEffect(() => {
    let stopped = false

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        })
        if (stopped) { stream.getTracks().forEach(t => t.stop()); return }
        streamRef.current = stream

        const video = videoRef.current
        video.srcObject = stream
        await video.play()

        const drawFrame = () => {
          if (stopped || !scanning) return
          const vw = video.videoWidth
          const vh = video.videoHeight
          if (!vw || !vh) { rafRef.current = requestAnimationFrame(drawFrame); return }

          // Draw full background view
          const bgCanvas = bgCanvasRef.current
          bgCanvas.width = vw
          bgCanvas.height = vh
          const bgCtx = bgCanvas.getContext('2d')
          bgCtx.drawImage(video, 0, 0, vw, vh)

          // Draw zoomed center crop
          const zoomCanvas = zoomCanvasRef.current
          const zoomSize = zoomCanvas.clientWidth * window.devicePixelRatio
          zoomCanvas.width = zoomSize
          zoomCanvas.height = zoomSize
          const zoomCtx = zoomCanvas.getContext('2d')

          const cropW = vw / ZOOM
          const cropH = vh / ZOOM
          const cropX = (vw - cropW) / 2
          const cropY = (vh - cropH) / 2
          zoomCtx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, zoomSize, zoomSize)

          rafRef.current = requestAnimationFrame(drawFrame)
        }

        drawFrame()

        // QR scanning loop on the zoomed area
        const scanLoop = () => {
          if (stopped || !scanning) return
          const zoomCanvas = zoomCanvasRef.current
          const w = zoomCanvas.width
          const h = zoomCanvas.height
          if (w && h) {
            const ctx = zoomCanvas.getContext('2d')
            const imageData = ctx.getImageData(0, 0, w, h)
            const result = jsQR(imageData.data, w, h, { inversionAttempts: 'dontInvert' })
            if (result && result.data) {
              handleCode(result.data.trim())
            }
          }
          scanTimerRef.current = setTimeout(scanLoop, SCAN_INTERVAL)
        }
        scanTimerRef.current = setTimeout(scanLoop, 500)

      } catch {
        if (!stopped) setError('Kunne ikke starte kameraet.')
      }
    }

    start()

    return () => {
      stopped = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (scanTimerRef.current) clearTimeout(scanTimerRef.current)
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    }
  }, [scanning, handleCode])

  return (
    <div className="screen center">
      <h2>Skann QR-koden din</h2>
      <p className="status-sub">Still deg i midten slik at QR-koden synes</p>

      <div className="qr-dual-view">
        <canvas ref={bgCanvasRef} className="qr-bg-canvas" />
        <div className="qr-zoom-ring">
          <canvas ref={zoomCanvasRef} className="qr-zoom-canvas" />
        </div>
      </div>
      <video ref={videoRef} playsInline muted style={{ display: 'none' }} />

      {error && <p className="qr-scan-error">{error}</p>}
      <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
    </div>
  )
}
