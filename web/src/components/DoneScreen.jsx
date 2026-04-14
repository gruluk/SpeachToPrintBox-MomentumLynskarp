export default function DoneScreen({ name, interest, onDone }) {
  const base = import.meta.env.BASE_URL || '/'

  return (
    <div className="screen center">
      <h2>Registrering fullført!</h2>
      <p className="status-sub">Du er registrert. Etiketten din skrives ut.</p>

      <div className="label-preview">
        <div className="label-preview-top">
          <img src={`${base}sopra_steria_logo.png`} className="label-preview-logo" alt="Sopra Steria" />
          <span className="label-preview-name">{name}</span>
        </div>
        <div className="label-preview-bottom">
          <span className="label-preview-interest">{interest || ''}</span>
        </div>
      </div>

      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
