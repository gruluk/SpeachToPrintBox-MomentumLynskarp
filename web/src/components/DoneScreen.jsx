export default function DoneScreen({ name, interest, onDone }) {
  return (
    <div className="screen center">
      <h2>Registrering fullfort!</h2>
      <p className="result-name">{name}</p>
      {interest && <p className="result-interest">{interest}</p>}
      <p className="status-sub">Du er registrert. Etiketten din skrives ut.</p>
      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
