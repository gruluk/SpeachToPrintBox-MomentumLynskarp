import { useEffect } from 'react'
import SceneDecorations from './SceneDecorations'

export default function WaitingScreen({ genReadyRef, genResultRef, genErrorRef, onReady, onError }) {
  useEffect(() => {
    const interval = setInterval(() => {
      if (genReadyRef.current) {
        clearInterval(interval)
        onReady(genResultRef.current)
      } else if (genErrorRef.current) {
        clearInterval(interval)
        onError()
      }
    }, 500)
    return () => clearInterval(interval)
  }, [genReadyRef, genResultRef, genErrorRef, onReady, onError])

  return (
    <div className="screen center">
      <SceneDecorations seed={6} />
      <div className="spinner" />
      <p className="status-text">Lager pikselkunst-portrettet ditt...</p>
      <p className="status-sub">Dette tar omtrent 30–60 sekunder</p>
    </div>
  )
}
