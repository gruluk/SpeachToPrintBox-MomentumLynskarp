import { useState, useEffect } from 'react'
import SceneDecorations from './SceneDecorations'

const base = import.meta.env.BASE_URL

const DINO_IMAGES = {
  '1': 'dino_1.png',
  '2': 'dino_2.png',
  '3': 'dino_3.png',
  '4': 'dino_4.png',
}

const EGG_IMAGES = {
  '1': 'dino_egg_1.png',
  '2': 'dino_egg_2.png',
  '3': 'dino_egg_3.png',
  '4': 'dino_egg_4.png',
}

// phase: 'egg' → 'flash' → 'reveal'
export default function DinoRevealScreen({ dinoKey, dinoName, onContinue }) {
  const [phase, setPhase] = useState('egg')

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('flash'),  2400)
    const t2 = setTimeout(() => setPhase('reveal'), 2750)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  if (phase === 'flash') {
    return <div className="dino-flash" />
  }

  if (phase === 'egg') {
    return (
      <div className="screen center">
        <SceneDecorations seed={5} />
        <img
          src={`${base}${EGG_IMAGES[dinoKey]}`}
          alt="dino egg"
          className="dino-egg-img"
        />
      </div>
    )
  }

  // reveal
  return (
    <div className="screen center dino-reveal-screen">
      <SceneDecorations seed={5} />
      <p className="dino-reveal-label">Du er en...</p>
      <img
        src={`${base}${DINO_IMAGES[dinoKey]}`}
        alt={dinoName}
        className="dino-reveal-img"
      />
      <h2 className="dino-reveal-name">{dinoName}!</h2>
      <button className="btn-start" onClick={onContinue}>
        La oss gå!
      </button>
    </div>
  )
}
