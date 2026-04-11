export default function DemoDoneScreen({ name, demo, onDone }) {
  return (
    <div className="screen center-content">
      <h2>Thanks {name}!</h2>
      <p className="status-text">Your demo request for <strong>{demo}</strong> has been noted.</p>
      <button className="btn-start" onClick={onDone}>Done</button>
    </div>
  )
}
