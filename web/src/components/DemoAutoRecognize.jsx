import { useEffect, useRef, useState } from 'react'

let _cachedStream = null
const ZOOM = 1.8
const MAX_ATTEMPTS = 5
const RETRY_DELAY = 1500 // ms between attempts

export default function DemoAutoRecognize({ onMatched, onNoMatch, onCancel }) {
  const videoRef = useRef(null)
  const attemptRef = useRef(0)
  const cancelledRef = useRef(false)
  const [status, setStatus] = useState('Starting camera...')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    cancelledRef.current = false

    async function run() {
      // Start camera (hidden)
      const stream = await getStream()
      if (!stream || cancelledRef.current) return

      const video = videoRef.current
      if (!video) return
      video.srcObject = stream
      await video.play()

      // Wait a moment for camera to stabilize
      await sleep(500)
      if (cancelledRef.current) return

      // Retry loop
      for (let i = 0; i < MAX_ATTEMPTS; i++) {
        if (cancelledRef.current) return
        attemptRef.current = i + 1
        setAttempt(i + 1)
        setStatus(i === 0 ? 'Recognizing...' : `Retrying... (${i + 1}/${MAX_ATTEMPTS})`)

        const blob = captureFrame(video)
        if (!blob) {
          await sleep(RETRY_DELAY)
          continue
        }

        try {
          const fd = new FormData()
          fd.append('image', blob, 'photo.jpg')
          fd.append('threshold', '0.6')
          const res = await fetch('/face/recognize', { method: 'POST', body: fd })
          const data = await res.json()

          if (cancelledRef.current) return

          if (data.ok && data.matched) {
            onMatched({ id: data.user_id, name: data.name, interest: data.interest })
            return
          }

          // No match or no face — retry
        } catch (e) {
          console.error('[auto-recognize] attempt failed:', e)
        }

        if (i < MAX_ATTEMPTS - 1) {
          await sleep(RETRY_DELAY)
        }
      }

      // All attempts exhausted
      if (!cancelledRef.current) {
        onNoMatch()
      }
    }

    run()

    return () => {
      cancelledRef.current = true
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [onMatched, onNoMatch])

  function handleCancel() {
    cancelledRef.current = true
    onCancel()
  }

  return (
    <div className="screen center">
      {/* Hidden video element for frame capture */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ position: 'absolute', opacity: 0, pointerEvents: 'none', width: 1, height: 1 }}
      />
      <div className="spinner" />
      <p className="status-text">{status}</p>
      {attempt > 1 && (
        <p className="status-sub">Hold still, looking for your face...</p>
      )}
      <button className="btn-secondary" onClick={handleCancel} style={{ marginTop: '2rem' }}>
        Cancel
      </button>
    </div>
  )
}

async function getStream() {
  if (_cachedStream && _cachedStream.getTracks().every(t => t.readyState === 'live')) {
    return _cachedStream
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    })
    _cachedStream = stream
    return stream
  } catch (e) {
    console.error('[camera]', e)
    return null
  }
}

function captureFrame(video) {
  if (!video || !video.videoWidth) return null
  const canvas = document.createElement('canvas')
  const sw = video.videoWidth / ZOOM
  const sh = video.videoHeight / ZOOM
  const sx = (video.videoWidth - sw) / 2
  const sy = (video.videoHeight - sh) / 2
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
  // Synchronous blob creation via toDataURL → convert to blob
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
  const binary = atob(dataUrl.split(',')[1])
  const array = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i)
  return new Blob([array], { type: 'image/jpeg' })
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
