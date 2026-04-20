export default function PrivacyScreen({ onAccept, onCancel }) {
  return (
    <div className="screen center">
      <div className="consent-screen">
        <h2 className="consent-title">Personvernserklæring</h2>
        <div className="consent-card" style={{ marginTop: '1.5rem' }}>
          <p style={{ fontSize: '1.1rem', lineHeight: '1.7', color: 'rgba(255,255,255,0.85)' }}>
            Du velger selv hvilke temaer du er interessert i. Interessene trykkes på klistrelappen din
            og brukes til å tilpasse foredrag og eventuelle demoer til dine interesser. Opplysningene
            slettes senest 3 måneder etter arrangementet.
          </p>
        </div>
      </div>
      <div className="btn-row" style={{ marginTop: '2rem' }}>
        <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
        <button className="btn-primary" onClick={onAccept}>Godta og fortsett</button>
      </div>
    </div>
  )
}
