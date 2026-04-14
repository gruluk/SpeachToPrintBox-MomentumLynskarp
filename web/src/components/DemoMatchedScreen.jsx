export default function DemoMatchedScreen({ matchedUser, onWantsDemo, onCancel }) {
  return (
    <div className="screen center">
      <p className="demo-greeting">Hei {matchedUser?.name}!</p>
      <h2>Vil du og din virksomhet ha demo, som vist på scenen?</h2>
      <div className="btn-row" style={{ marginTop: '1.5rem' }}>
        <button className="btn-cancel" onClick={onCancel}>Nei takk</button>
        <button className="btn-start" onClick={onWantsDemo}>Ja, jeg vil ha demo!</button>
      </div>
      <p className="name-help-text">Er ikke dette deg? Ta kontakt med en av våre ansatte for hjelp.</p>
    </div>
  )
}
