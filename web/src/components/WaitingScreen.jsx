import { useEffect } from 'react'

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
      <div className="spinner" />
      <p className="status-text">Creating your label...</p>
      <p className="status-sub">This takes about 30–60 seconds</p>
    </div>
  )
}
