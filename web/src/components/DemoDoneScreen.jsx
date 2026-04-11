export default function DemoDoneScreen({ name, demoCount, onDone }) {
  return (
    <div className="screen center">
      <h2>Thanks {name}!</h2>
      <p className="status-text">
        {demoCount === 1
          ? 'Your demo request has been noted.'
          : `Your ${demoCount} demo requests have been noted.`}
      </p>
      <button className="btn-start" onClick={onDone}>Done</button>
    </div>
  )
}
