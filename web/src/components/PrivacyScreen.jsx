import { useState } from 'react'

export default function PrivacyScreen({
  title = 'Samtykke til bruk av dine opplysninger',
  bullets = [],
  checkboxLabel = 'Jeg samtykker til at Sopra Steria lagrer og behandler opplysningene mine slik det er beskrevet over.',
  onAccept,
  onCancel,
}) {
  const [accepted, setAccepted] = useState(false)

  return (
    <div className="screen center">
      <div className="consent-screen">
        <h2 className="consent-title">{title}</h2>

        <div className="consent-card" style={{ marginTop: '1.5rem' }}>
          <ul className="consent-list">
            {bullets.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
        </div>

        <label className="consent-check">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
          />
          <span>{checkboxLabel}</span>
        </label>
      </div>

      <div className="btn-row" style={{ marginTop: '2rem' }}>
        <button className="btn-cancel" type="button" onClick={onCancel}>
          Avbryt
        </button>
        <button className="btn-primary" type="button" onClick={onAccept} disabled={!accepted}>
          Neste
        </button>
      </div>
    </div>
  )
}
