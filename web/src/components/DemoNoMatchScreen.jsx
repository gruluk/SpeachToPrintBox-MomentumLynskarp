export default function DemoNoMatchScreen({ onRetry, onRegister, onBack }) {
  return (
    <div className="screen center-content">
      <h2>We couldn't recognize you</h2>
      <p className="status-text">Make sure you've registered at the booth first.</p>
      <div className="start-buttons">
        <button className="btn-primary" onClick={onRetry}>Try again</button>
        <button className="btn-secondary" onClick={onRegister}>Register instead</button>
      </div>
      <button className="btn-secondary" onClick={onBack} style={{ marginTop: '1rem' }}>Back</button>
    </div>
  )
}
