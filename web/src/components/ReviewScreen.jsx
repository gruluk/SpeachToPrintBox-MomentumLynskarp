export default function ReviewScreen({ photoUrl, validating, onOk, onRetake }) {
  return (
    <div className="screen center">
      <h2>How's this?</h2>
      <div className="camera-circle">
        <img src={photoUrl} alt="Your photo" className="review-photo" />
        {validating && (
          <div className="validate-overlay">
            <p className="validate-text">Checking...</p>
          </div>
        )}
      </div>
      <div className="btn-row">
        <button className="btn-secondary" onClick={onRetake} disabled={validating}>Retake</button>
        <button className="btn-primary" onClick={onOk} disabled={validating}>Looks Good!</button>
      </div>
    </div>
  )
}
