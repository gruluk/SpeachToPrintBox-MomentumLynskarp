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
      <h2>Vi kjenner deg ikke igjen</h2>
      <p className="status-sub">Du må kanskje registrere deg først.</p>
      <div className="demo-options" style={{ marginTop: '1.5rem' }}>
        <button className="btn-primary" onClick={onRetry}>Prøv igjen</button>
        <button className="btn-secondary" onClick={onRegister}>Registrer deg</button>
        <button className="btn-secondary" onClick={onBack}>Tilbake</button>
      </div>
    </div>
  )
}
