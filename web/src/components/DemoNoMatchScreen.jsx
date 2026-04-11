import { DotLottieReact } from '@lottiefiles/dotlottie-react'

const base = import.meta.env.BASE_URL

export default function DemoNoMatchScreen({ onRetry, onRegister, onBack }) {
  return (
    <div className="screen center">
      <div className="recognize-eye">
        <DotLottieReact
          src={`${base}Eye.lottie`}
          loop
          autoplay
          style={{ width: '140px', height: '140px' }}
        />
      </div>
      <h2>We don't recognize you</h2>
      <p className="status-sub">You may need to register first.</p>
      <div className="demo-options" style={{ marginTop: '1.5rem' }}>
        <button className="btn-primary" onClick={onRetry}>Try again</button>
        <button className="btn-secondary" onClick={onRegister}>Register instead</button>
        <button className="btn-secondary" onClick={onBack}>Back</button>
      </div>
    </div>
  )
}
