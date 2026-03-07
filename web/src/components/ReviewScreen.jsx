export default function ReviewScreen({ photoUrl, onOk, onRetake }) {
  return (
    <div className="screen center">
      <h2>How's this?</h2>
      <img src={photoUrl} alt="Your photo" className="review-photo" />
      <div className="btn-row">
        <button className="btn-secondary" onClick={onRetake}>Retake</button>
        <button className="btn-primary" onClick={onOk}>Looks Good!</button>
      </div>
    </div>
  )
}
