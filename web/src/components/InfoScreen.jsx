export default function InfoScreen({ onContinue, onCancel }) {
  return (
    <div className="screen center consent-screen">
      <h2 className="consent-title">Velkommen til Lynskarp</h2>
      <p className="consent-subtitle">Les hva du samtykker til og godkjenn.</p>

      <p className="consent-voluntary">
        Samtykket er frivillig. Ønsker du ikke å samtykke, kan du sjekke inn
        manuelt ved registreringsdisken. Du kan trekke tilbake samtykket når
        som helst under arrangementet.
      </p>

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

      <div className="btn-row">
        <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
        <button className="btn-start" onClick={onContinue}>Bekreft og skann</button>
      </div>
    </div>
  )
}
