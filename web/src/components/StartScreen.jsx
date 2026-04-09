const base = import.meta.env.BASE_URL

export default function StartScreen({ onStart, errorMsg }) {
  return (
    <div className="screen start-screen">
      <div className="start-content">
        <img src={`${base}logo.png`} className="start-logo" alt="Sopra Steria" />
        <p className="subtitle">Få din pixel-avatar!</p>
        {errorMsg && <p className="error">{errorMsg}</p>}
        <button className="btn-start" onClick={onStart}>Start</button>
      </div>
    </div>
  )
}
