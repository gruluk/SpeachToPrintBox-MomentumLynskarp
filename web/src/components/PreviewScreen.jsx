import { useEffect, useRef, useState } from 'react'

export default function PreviewScreen({ onCapture, errorMsg }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [countdown, setCountdown] = useState(null)
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    let active = true

    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        })
        if (!active) {
          stream.getTracks().forEach(t => t.stop())
          return
        }
        streamRef.current = stream
        const video = videoRef.current
        video.srcObject = stream
        video.play()
      } catch (e) {
        console.error('[camera]', e)
      }
    }

    startCamera()
    return () => {
      active = false
      streamRef.current?.getTracks().forEach(t => t.stop())
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
      streamRef.current?.getTracks().forEach(t => t.stop())
      onCapture(blob)
    }, 'image/jpeg', 0.92)
  }

  return (
    <div className="screen preview-screen">
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
      {errorMsg && <p className="error overlay-error">{errorMsg}</p>}
      <button
        className="btn-capture"
        onClick={capture}
        disabled={capturing}
      >
        {capturing ? '...' : '📸 Take Photo'}
      </button>
    </div>
  )
}
