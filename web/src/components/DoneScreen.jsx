export default function DoneScreen({ name, interest, userId, onDone }) {
  return (
    <div className="screen center">
      <h2>Registrering fullført!</h2>
      <p className="status-sub">Du er registrert. Etiketten din skrives ut.</p>

      {userId && (
        <div className="printer-anim">
          <div className="printer-slot" />
          <div className="printer-paper">
            <div className="label-preview">
              <img
                src={`/label-preview/${userId}`}
                alt="Etikett-forhåndsvisning"
                className="label-preview-img"
              />
            </div>
          </div>
        </div>
      )}

      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
