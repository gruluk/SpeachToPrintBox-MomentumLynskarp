export default function InfoScreen({ onContinue, onCancel }) {
  return (
    <div className="screen center">
      <h2 className="info-title">Personverninformasjon</h2>
      <p className="info-body">
        Vi tar et bilde av deg for ansiktsgjenkjenning<br />
        slik at vi kan kjenne deg igjen senere.
      </p>
      <p className="info-body">
        Selve bildet lagres ikke. Kun en anonym<br />
        ansiktsprofil lagres midlertidig under arrangementet.
      </p>
      <div className="btn-row">
        <button className="btn-cancel" onClick={onCancel}>Avbryt</button>
        <button className="btn-start" onClick={onContinue}>Forstått, la oss starte!</button>
      </div>
    </div>
  )
}
