import { useEffect, useRef, useState } from 'react'
import { DotLottieReact } from '@lottiefiles/dotlottie-react'

let _cachedStream = null
const ZOOM = 1.8
const MAX_ATTEMPTS = 5
const RETRY_DELAY = 1500 // ms between attempts

const base = import.meta.env.BASE_URL

export default function DemoAutoRecognize({ onMatched, onNoMatch, onCancel }) {
  const videoRef = useRef(null)
  const cancelledRef = useRef(false)
  const [attempt, setAttempt] = useState(0)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    cancelledRef.current = false

    async function run() {
      const stream = await getStream()
      if (!stream || cancelledRef.current) return

      const video = videoRef.current
      if (!video) return
      video.srcObject = stream
      await video.play()

      await sleep(500)
      if (cancelledRef.current) return

      for (let i = 0; i < MAX_ATTEMPTS; i++) {
        if (cancelledRef.current) return
        setAttempt(i + 1)

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
        } catch (e) {
          console.error('[auto-recognize] attempt failed:', e)
        }

        if (i < MAX_ATTEMPTS - 1) {
          await sleep(RETRY_DELAY)
        }
      }

      if (!cancelledRef.current) {
        setFailed(true)
      }
    }

    run()

    return () => {
      cancelledRef.current = true
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [onMatched])

  const statusText = failed
    ? "We don't recognize you"
    : attempt <= 2
      ? 'Finding your information...'
      : 'Still trying to figure it out...'

  return (
    <div className="screen center">
      {/* Hidden video for frame capture */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ position: 'absolute', opacity: 0, pointerEvents: 'none', width: 1, height: 1 }}
      />

      <div className="recognize-eye">
        <DotLottieReact
          src={`${base}Eye.lottie`}
          loop
          autoplay
          style={{ width: '180px', height: '180px' }}
        />
      </div>

      <p className="status-text">{statusText}</p>

      {failed ? (
        <div className="recognize-failed">
          <p className="status-sub">You may need to register first.</p>
          <div className="start-buttons" style={{ marginTop: '1.5rem' }}>
            <button className="btn-primary" onClick={() => { cancelledRef.current = true; onNoMatch() }}>
              Try again
            </button>
            <button className="btn-secondary" onClick={() => { cancelledRef.current = true; onCancel() }}>
              Back
            </button>
          </div>
        </div>
      ) : (
        <button className="btn-secondary" onClick={() => { cancelledRef.current = true; onCancel() }} style={{ marginTop: '2rem' }}>
          Cancel
        </button>
      )}
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
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
  const binary = atob(dataUrl.split(',')[1])
  const array = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i)
  return new Blob([array], { type: 'image/jpeg' })
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
