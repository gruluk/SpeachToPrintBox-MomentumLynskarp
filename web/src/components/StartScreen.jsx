const base = import.meta.env.BASE_URL

export default function StartScreen({ onStart, errorMsg }) {
  return (
    <div className="screen start-screen">
      {/* Corner dinos */}
      <img src={`${base}dino_4.png`} className="dino dino-tl" alt="" />
      <img src={`${base}dino_3.png`} className="dino dino-tr" alt="" />
      <img src={`${base}dino_1.png`} className="dino dino-bl" alt="" />
      <img src={`${base}dino_2.png`} className="dino dino-br" alt="" />

      {/* Center content */}
      <div className="start-content">
        <img src={`${base}logo_figma.png`} className="start-logo" alt="Bytefest '26" />
        <p className="subtitle">Get your pixel art portrait!</p>
        {errorMsg && <p className="error">{errorMsg}</p>}
        <button className="btn-primary btn-start" onClick={onStart}>Start</button>
      </div>
    </div>
  )
}
