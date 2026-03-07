import SceneDecorations from './SceneDecorations'

const base = import.meta.env.BASE_URL

const DINO_IMAGES = {
  '1': 'dino_1.png',
  '2': 'dino_2.png',
  '3': 'dino_3.png',
  '4': 'dino_4.png',
}

export default function DinoRevealScreen({ dinoKey, dinoName, onContinue }) {
  return (
    <div className="screen center">
      <SceneDecorations seed={5} />
      <p className="dino-reveal-label">You are a...</p>
      <img
        src={`${base}${DINO_IMAGES[dinoKey]}`}
        alt={dinoName}
        className="dino-reveal-img"
      />
      <h2 className="dino-reveal-name">{dinoName}!</h2>
      <button className="btn-start" onClick={onContinue}>
        Let's go!
      </button>
    </div>
  )
}
