import { useState } from 'react'

const BULLETS = [
  'Vi lagrer navn, epost, telefonnummer og valgte interesseområder for å administrere din deltakelse på Lynskarp.',
  'Opplysningene brukes til å bekrefte registrering, lage navneskilt og eventuell oppfølging etter arrangementet.',
  'Du kan når som helst trekke samtykke tilbake ved å kontakte oss.',
  'All data slettes senest 90 dager etter at arrangementet er avsluttet.',
]

export default function PrivacyScreen({ onAccept, onCancel }) {
  const [accepted, setAccepted] = useState(false)

  return (
    <div className="screen center">
      <div className="consent-screen">
        <h2 className="consent-title">Samtykke til bruk av dine opplysninger</h2>

        <div className="consent-card" style={{ marginTop: '1.5rem' }}>
          <ul className="consent-list">
            {BULLETS.map((text) => (
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
          <span>
            Jeg samtykker til at Sopra Steria lagrer og behandler opplysningene mine slik det er
            beskrevet over.
          </span>
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
