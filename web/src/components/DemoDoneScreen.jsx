export default function DemoDoneScreen({ name, onDone }) {
  return (
    <div className="screen center">
      <h2>Takk {name}!</h2>
      <p className="status-text">
        Demoforespørselen din er registrert.
      </p>
      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
