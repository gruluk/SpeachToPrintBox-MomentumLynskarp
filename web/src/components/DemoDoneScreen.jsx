export default function DemoDoneScreen({ name, demoCount, onDone }) {
  return (
    <div className="screen center">
      <h2>Takk {name}!</h2>
      <p className="status-text">
        {demoCount === 1
          ? 'Demoforespørselen din er registrert.'
          : `Dine ${demoCount} demoforespørsler er registrert.`}
      </p>
      <button className="btn-start" onClick={onDone}>Ferdig</button>
    </div>
  )
}
