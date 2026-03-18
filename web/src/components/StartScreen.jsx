import { useEffect, useRef, useState } from 'react'

const base = import.meta.env.BASE_URL

export default function StartScreen({ onStart, errorMsg }) {
  const [meteorStyle, setMeteorStyle] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => {
    function scheduleMeteor() {
      const delay = 8000 + Math.random() * 12000 // 8–20 s between passes
      timerRef.current = setTimeout(() => {
        const startTop = Math.random() * 25 - 5 // –5vh to 20vh
        setMeteorStyle({ top: `${startTop}vh` })
        setTimeout(() => {
          setMeteorStyle(null)
          scheduleMeteor()
        }, 2800)
      }, delay)
    }
    scheduleMeteor()
    return () => clearTimeout(timerRef.current)
  }, [])

  return (
    <div className="screen start-screen">
      {/* Meteor — behind everything */}
      {meteorStyle && (
        <img src={`${base}meteor_1.png`} className="meteor" style={meteorStyle} alt="" />
      )}

      {/* Pterodactyl hovering */}
      <img src={`${base}dino_4.png`} className="dino-pterodactyl" alt="" />

      {/* Centre content */}
      <div className="start-content">
        <img src={`${base}logo_figma.png`} className="start-logo" alt="Bytefest '26" />
        <p className="subtitle">Få din avatar på skjermen!</p>
        {errorMsg && <p className="error">{errorMsg}</p>}
        <button className="btn-start" onClick={onStart}>Start</button>
      </div>

      {/* Ground scene */}
      <div className="ground-scene">
        <img src={`${base}bush_4.png`}  className="ground-asset" style={{left:'0',           width:'min(130px,15vw)'}} alt="" />
        <img src={`${base}dino_3.png`}  className="ground-asset" style={{left:'8%',          width:'min(140px,16vw)'}} alt="" />
        <img src={`${base}bush_2.png`}  className="ground-asset" style={{left:'24%',         width:'min(90px,11vw)'}} alt="" />
        <img src={`${base}dino_1.png`}  className="ground-asset" style={{left:'50%', transform:'translateX(-50%)', width:'min(115px,13vw)'}} alt="" />
        <img src={`${base}bush_1.png`}  className="ground-asset" style={{left:'57%',         width:'min(150px,17vw)'}} alt="" />
        <img src={`${base}dino_2.png`}  className="ground-asset" style={{right:'10%',        width:'min(130px,15vw)'}} alt="" />
        <img src={`${base}bush_3.png`}  className="ground-asset" style={{right:'0',          width:'min(110px,13vw)'}} alt="" />
      </div>
    </div>
  )
}
