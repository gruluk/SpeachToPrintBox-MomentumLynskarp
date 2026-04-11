import { useEffect, useRef, useState, useCallback } from 'react'

let _cachedStream = null
const ZOOM = 1.8

export default function FaceDebugScreen() {
  const videoRef = useRef(null)
  const [logs, setLogs] = useState([])
  const [users, setUsers] = useState([])
  const [enrollName, setEnrollName] = useState('')
  const [enrollInterest, setEnrollInterest] = useState('')
  const [busy, setBusy] = useState(false)
  const [threshold, setThreshold] = useState(0.6)
  const logEndRef = useRef(null)

  const addLog = useCallback((type, text, detail = null) => {
    setLogs(prev => [...prev, {
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString(),
      type,
      text,
      detail,
    }])
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Camera setup
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
        addLog('info', 'Camera started')
      } catch (e) {
        addLog('error', `Camera error: ${e.message}`)
      }
    }
    startCamera()
    return () => {
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [addLog])

  // Load enrolled users on mount
  useEffect(() => { refreshUsers() }, [])

  async function refreshUsers() {
    try {
      const res = await fetch('/face/users')
      const data = await res.json()
      setUsers(data)
    } catch (e) {
      addLog('error', `Failed to load users: ${e.message}`)
    }
  }

  function captureFrame() {
    const video = videoRef.current
    if (!video) return null
    const canvas = document.createElement('canvas')
    const sw = video.videoWidth / ZOOM
    const sh = video.videoHeight / ZOOM
    const sx = (video.videoWidth - sw) / 2
    const sy = (video.videoHeight - sh) / 2
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
    return new Promise(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.92)
    })
  }

  async function handleEnroll() {
    if (!enrollName.trim()) return
    setBusy(true)
    addLog('info', `Enrolling "${enrollName}"...`)

    const blob = await captureFrame()
    if (!blob) { addLog('error', 'No frame captured'); setBusy(false); return }
    addLog('info', `Captured image (${(blob.size / 1024).toFixed(0)} KB)`)

    const fd = new FormData()
    fd.append('image', blob, 'photo.jpg')
    fd.append('name', enrollName.trim())
    fd.append('interest', enrollInterest.trim())

    try {
      const res = await fetch('/face/enroll', { method: 'POST', body: fd })
      const data = await res.json()

      if (data.ok) {
        addLog('success', `Enrolled "${data.name}" (${data.embedding_dims}-dim embedding)`)
        addLog('timing', `Embedding computed in ${data.time_ms}ms`)
        setEnrollName('')
        setEnrollInterest('')
        refreshUsers()
      } else if (data.error === 'no_face') {
        addLog('error', `No face detected in image`)
        addLog('timing', `Processing took ${data.time_ms}ms`)
      } else {
        addLog('error', `Enroll failed: ${JSON.stringify(data)}`)
      }
    } catch (e) {
      addLog('error', `Enroll request failed: ${e.message}`)
    }
    setBusy(false)
  }

  async function handleRecognize() {
    setBusy(true)
    addLog('info', `Recognizing face (threshold: ${threshold})...`)

    const blob = await captureFrame()
    if (!blob) { addLog('error', 'No frame captured'); setBusy(false); return }
    addLog('info', `Captured image (${(blob.size / 1024).toFixed(0)} KB)`)

    const fd = new FormData()
    fd.append('image', blob, 'photo.jpg')
    fd.append('threshold', threshold.toString())

    try {
      const res = await fetch('/face/recognize', { method: 'POST', body: fd })
      const data = await res.json()

      if (!data.ok && data.error === 'no_face') {
        addLog('error', 'No face detected in image')
        addLog('timing', `Processing took ${data.time_ms}ms`)
      } else if (data.matched) {
        addLog('match', `MATCH: ${data.name} (distance: ${data.distance}, interest: ${data.interest || 'n/a'})`)
        addLog('timing', `Embedding computed in ${data.time_ms}ms`)
        if (data.all_scores?.length > 0) {
          addLog('scores', 'All scores:', data.all_scores)
        }
      } else {
        const bestDist = data.distance != null ? ` (best: ${data.distance})` : ''
        addLog('no_match', `NO MATCH${bestDist} — threshold: ${data.threshold}`)
        addLog('timing', `Embedding computed in ${data.time_ms}ms`)
        if (data.all_scores?.length > 0) {
          addLog('scores', 'All scores:', data.all_scores)
        }
      }
    } catch (e) {
      addLog('error', `Recognize request failed: ${e.message}`)
    }
    setBusy(false)
  }

  async function handleDeleteUser(userId) {
    try {
      await fetch(`/face/users/${userId}`, { method: 'DELETE' })
      addLog('info', `Deleted user ${userId.slice(0, 8)}...`)
      refreshUsers()
    } catch (e) {
      addLog('error', `Delete failed: ${e.message}`)
    }
  }

  function clearLogs() {
    setLogs([])
  }

  const logColor = {
    info: '#6b9bd2',
    success: '#4caf50',
    error: '#ef5350',
    timing: '#ffc107',
    match: '#4caf50',
    no_match: '#ef5350',
    scores: '#9e9e9e',
  }

  return (
    <div className="face-debug">
      <div className="face-debug-header">
        <h2>Face Recognition Debug</h2>
        <span className="face-debug-count">{users.length} enrolled</span>
      </div>

      <div className="face-debug-layout">
        {/* Camera + Controls */}
        <div className="face-debug-camera-panel">
          <div className="face-debug-camera-wrap">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="face-debug-video"
              style={{ transform: `scale(${ZOOM}) scaleX(-1)` }}
            />
          </div>

          <div className="face-debug-controls">
            <div className="face-debug-enroll-form">
              <input
                type="text"
                placeholder="Name"
                value={enrollName}
                onChange={e => setEnrollName(e.target.value)}
                maxLength={40}
              />
              <input
                type="text"
                placeholder="Interest (e.g. Accounting)"
                value={enrollInterest}
                onChange={e => setEnrollInterest(e.target.value)}
                maxLength={60}
              />
              <button onClick={handleEnroll} disabled={busy || !enrollName.trim()}>
                Enroll Face
              </button>
            </div>

            <div className="face-debug-recognize-form">
              <label>
                Threshold:
                <input
                  type="range"
                  min="0.3"
                  max="0.9"
                  step="0.05"
                  value={threshold}
                  onChange={e => setThreshold(parseFloat(e.target.value))}
                />
                <span>{threshold.toFixed(2)}</span>
              </label>
              <button onClick={handleRecognize} disabled={busy}>
                Recognize Face
              </button>
            </div>
          </div>
        </div>

        {/* Log Panel */}
        <div className="face-debug-log-panel">
          <div className="face-debug-log-header">
            <span>Logs</span>
            <button onClick={clearLogs}>Clear</button>
          </div>
          <div className="face-debug-log-area">
            {logs.map(log => (
              <div key={log.id} className="face-debug-log-entry" style={{ borderLeftColor: logColor[log.type] || '#666' }}>
                <span className="face-debug-log-time">{log.time}</span>
                <span className="face-debug-log-text" style={{ color: logColor[log.type] || '#ccc' }}>
                  {log.text}
                </span>
                {log.detail && (
                  <div className="face-debug-log-detail">
                    <table>
                      <thead>
                        <tr><th>Name</th><th>Interest</th><th>Distance</th></tr>
                      </thead>
                      <tbody>
                        {log.detail.map((s, i) => (
                          <tr key={i} className={s.distance <= threshold ? 'score-match' : ''}>
                            <td>{s.name}</td>
                            <td>{s.interest || '-'}</td>
                            <td>{s.distance}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>

      {/* Enrolled Users */}
      <div className="face-debug-users">
        <h3>Enrolled Users</h3>
        {users.length === 0 && <p className="face-debug-empty">No users enrolled yet</p>}
        <div className="face-debug-user-list">
          {users.map(u => (
            <div key={u.id} className="face-debug-user-card">
              <div>
                <strong>{u.name}</strong>
                {u.interest && <span className="face-debug-interest">{u.interest}</span>}
              </div>
              <button onClick={() => handleDeleteUser(u.id)}>Delete</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
