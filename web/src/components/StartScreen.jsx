const base = import.meta.env.BASE_URL

export default function StartScreen({
  mode = 'both',
  showRegister,
  showCheckout,
  onRegister,
  onDemo,
  errorMsg,
}) {
  const canRegister =
    showRegister !== undefined ? showRegister : mode === 'both' || mode === 'register'
  const canCheckout =
    showCheckout !== undefined ? showCheckout : mode === 'both' || mode === 'demo'

  return (
    <div className="screen start-screen">
      <div className="start-content">
        <img src={`${base}sopra-steria-logo-white.png`} className="start-logo" alt="Sopra Steria" />
        <p className="subtitle">Velkommen!</p>
        {errorMsg && <p className="error">{errorMsg}</p>}
        <div className="start-buttons">
          {canRegister && (
            <button className="btn-start" onClick={onRegister}>
              Registrer deg
            </button>
          )}
          {canCheckout && (
            <button className="btn-primary" onClick={onDemo}>
              Sjekk ut her
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
