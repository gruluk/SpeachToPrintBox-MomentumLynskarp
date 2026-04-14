const base = import.meta.env.BASE_URL

export default function StartScreen({ mode = 'both', onRegister, onDemo, errorMsg }) {
  return (
    <div className="screen start-screen">
      <div className="start-content">
        <img src={`${base}logo.png`} className="start-logo" alt="Momentum Lynskarp" />
        <p className="subtitle">Velkommen!</p>
        {errorMsg && <p className="error">{errorMsg}</p>}
        <div className="start-buttons">
          {(mode === 'both' || mode === 'register') && (
            <button className="btn-start" onClick={onRegister}>Registrer deg</button>
          )}
          {(mode === 'both' || mode === 'demo') && (
            <button className="btn-primary" onClick={onDemo}>Trykk her</button>
          )}
        </div>
      </div>
    </div>
  )
}
