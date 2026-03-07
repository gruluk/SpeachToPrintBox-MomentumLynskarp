export default function StartScreen({ onStart, errorMsg }) {
  return (
    <div className="screen center">
      <h1 className="title">Bytefest '26</h1>
      <p className="subtitle">Get your pixel art portrait!</p>
      {errorMsg && <p className="error">{errorMsg}</p>}
      <button className="btn-primary" onClick={onStart}>Start</button>
    </div>
  )
}
