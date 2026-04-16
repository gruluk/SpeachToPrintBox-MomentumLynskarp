import { useState } from 'react'

export default function InfoScreen({ onContinue, onCancel }) {
  const [consented, setConsented] = useState(false)

  return (
    <div className="screen consent-screen">
      <h2 className="consent-title">Velkommen til Lynskarp</h2>
      <p className="consent-subtitle">Les hva du samtykker til og godkjenn.</p>

      <div className="consent-notice">
        <span className="consent-notice-icon">i</span>
        <p>
          Samtykket er frivillig. Ønsker du ikke å samtykke, kan du sjekke inn
          manuelt ved registreringsdisken. Du kan trekke tilbake samtykket når
          som helst under arrangementet.
        </p>
      </div>

      <div className="consent-card">
        <h3>Ansiktsgjenkjenning for innsjekking og utsjekking</h3>
        <p>
          Vi lager en biometrisk mal av ansiktet ditt som brukes til automatisk
          registrering av ankomst og avgang i dag. Malen slettes senest{' '}
          <strong>48 timer</strong> etter arrangementet — ingen videredeling.
        </p>
      </div>

      <div className="consent-card">
        <h3>Registrering av interesseområder</h3>
        <p>
          Du velger selv hvilke temaer du er interessert i. Interessene trykkes
          på klistrelappen din og kan brukes til å tilpasse en eventuell demo
          dersom du registrerer deg for det. Interessene slettes senest{' '}
          <strong>3 måneder</strong> etter arrangementet.
        </p>
      </div>

      <p className="consent-link-text">
        Les vår{' '}
        <a
          href="https://www.soprasteria.no/personvern"
          target="_blank"
          rel="noopener noreferrer"
          className="consent-link"
        >
          personvernerklæring for Lynskarp
        </a>{' '}
        for fullstendig informasjon.
      </p>

      <label className="consent-checkbox-wrapper">
        <input
          type="checkbox"
          checked={consented}
          onChange={(e) => setConsented(e.target.checked)}
        />
        <span>Jeg samtykker til begge punktene ovenfor</span>
      </label>

      <div className="btn-row">
        <button className="btn-cancel" onClick={onCancel}>Manuell innsjekking</button>
        <button
          className="btn-start"
          onClick={onContinue}
          disabled={!consented}
        >
          Bekreft og skann
        </button>
      </div>
    </div>
  )
}
