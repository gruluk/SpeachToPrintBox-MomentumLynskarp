import SceneDecorations from './SceneDecorations'

export default function ReviewScreen({ photoUrl, validating, onOk, onRetake }) {
  return (
    <div className="screen center">
      <SceneDecorations seed={2} />
      <h2>Ser dette bra ut?</h2>
      <div className="camera-circle">
        <img src={photoUrl} alt="Your photo" className="review-photo" />
        {validating && (
          <div className="validate-overlay">
            <p className="validate-text">Sjekker...</p>
          </div>
        )}
      </div>
      <div className="btn-row">
        <button className="btn-secondary" onClick={onRetake} disabled={validating}>Ta om igjen</button>
        <button className="btn-primary" onClick={onOk} disabled={validating}>Ser bra ut!</button>
      </div>
    </div>
  )
}
