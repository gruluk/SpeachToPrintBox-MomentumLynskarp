export default function InfoScreen({ onContinue, onBack }) {
  return (
    <div className="screen center">
      <h2 className="info-title">Personverninformasjon</h2>
      <p className="info-body">
        Bildet ditt behandles av OpenAI for å lage<br />
        en piksel-avatar av deg.
      </p>
      <p className="info-body">
        Selve bildet lagres ikke, kun avataren din<br />
        lagres midlertidig under arrangementet.
      </p>
      <div className="btn-row">
        <button className="btn-secondary" onClick={onBack}>Tilbake</button>
        <button className="btn-start" onClick={onContinue}>Forstått, la oss starte!</button>
      </div>
    </div>
  )
}
