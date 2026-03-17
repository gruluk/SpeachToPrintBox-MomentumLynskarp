import { useEffect, useRef, useState } from 'react'

// Keep the stream alive across component mounts so iOS only asks for
// camera permission once per session instead of on every retake.
let _cachedStream = null

export default function PreviewScreen({ onCapture, onCancel, errorMsg }) {
  const videoRef = useRef(null)
  const [countdown, setCountdown] = useState(null)
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    async function startCamera() {
      // Reuse existing stream if its tracks are still live
      if (_cachedStream && _cachedStream.getTracks().every(t => t.readyState === 'live')) {
        videoRef.current.srcObject = _cachedStream
        videoRef.current.play()
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        })
        _cachedStream = stream
        videoRef.current.srcObject = stream
        videoRef.current.play()
      } catch (e) {
        console.error('[camera]', e)
      }
    }

    startCamera()
    // Detach from video on unmount but keep tracks running to avoid re-prompting
    return () => {
      const video = videoRef.current
      if (video) video.srcObject = null
    }
  }, [])

  function capture() {
    if (capturing) return
    setCapturing(true)
    let count = 3
    setCountdown(count)
    const interval = setInterval(() => {
      count--
      if (count > 0) {
        setCountdown(count)
      } else {
        clearInterval(interval)
        setCountdown(null)
        doCapture()
      }
    }, 1000)
  }

  function doCapture() {
    const video = videoRef.current
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    // Do NOT mirror — server needs un-mirrored image
    ctx.drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      onCapture(blob)
    }, 'image/jpeg', 0.92)
  }

  return (
    <div className="screen preview-screen">
      {capturing && <div className="ring-light-overlay" />}
      <p className="camera-hint">Plasser ansiktet ditt i sirkelen</p>
      <div className="camera-circle">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-video"
        />
        {countdown !== null && (
          <div className="countdown">{countdown}</div>
        )}
      </div>
      {errorMsg && <p className="error">{errorMsg}</p>}
      <div className="capture-bar">
        <button
          className="btn-secondary btn-cancel"
          onClick={onCancel}
          disabled={capturing}
        >
          Avbryt
        </button>
        <button
          className="btn-capture"
          onClick={capture}
          disabled={capturing}
        >
          {capturing ? '...' : 'Ta bilde'}
        </button>
      </div>
    </div>
  )
}
