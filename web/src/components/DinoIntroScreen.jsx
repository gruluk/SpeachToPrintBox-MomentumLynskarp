import SceneDecorations from './SceneDecorations'

const base = import.meta.env.BASE_URL

const DINOS = [
  { src: 'dino_1.png', name: 'Brachiosaurus' },
  { src: 'dino_2.png', name: 'Triceratops' },
  { src: 'dino_3.png', name: 'Stegosaurus' },
  { src: 'dino_4.png', name: 'Pterodactyl' },
]

export default function DinoIntroScreen({ onContinue }) {
  return (
    <div className="screen center">
      <SceneDecorations seed={9} />
      <h2 className="dino-intro-title">Which dino are you?</h2>
      <p className="dino-intro-sub">
        Answer a few questions and we'll figure out which dinosaur matches your personality!
      </p>
      <div className="dino-intro-row">
        {DINOS.map(({ src, name }) => (
          <img
            key={src}
            src={`${base}${src}`}
            alt={name}
            className="dino-intro-img"
          />
        ))}
      </div>
      <button className="btn-start" onClick={onContinue}>
        Find my dino!
      </button>
    </div>
  )
}
