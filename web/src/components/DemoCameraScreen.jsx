import { useEffect, useRef, useState } from 'react'

let _cachedStream = null
const ZOOM = 1.8

export default function DemoCameraScreen({ onCapture, onCancel }) {
  const videoRef = useRef(null)
  const [countdown, setCountdown] = useState(null)
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    async function startCamera() {
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
    return () => {
      if (videoRef.current) videoRef.current.srcObject = null
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
    const sw = video.videoWidth / ZOOM
    const sh = video.videoHeight / ZOOM
    const sx = (video.videoWidth - sw) / 2
    const sy = (video.videoHeight - sh) / 2
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
    canvas.toBlob((blob) => {
      onCapture(blob)
    }, 'image/jpeg', 0.92)
  }

  return (
    <div className="screen preview-screen">
      {capturing && <div className="ring-light-overlay" />}
      <p className="camera-hint">Let's see who you are!</p>
      <div className="camera-circle">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-video"
          style={{ transform: `scale(${ZOOM}) scaleX(-1)` }}
        />
        {countdown !== null && (
          <div className="countdown">{countdown}</div>
        )}
      </div>
      <div className="capture-bar">
        <button className="btn-secondary btn-cancel" onClick={onCancel} disabled={capturing}>
          Back
        </button>
        <button className="btn-capture" onClick={capture} disabled={capturing}>
          {capturing ? '...' : 'Take photo'}
        </button>
      </div>
    </div>
  )
}
