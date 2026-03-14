import { useEffect, useRef } from 'react'
import SceneDecorations from './SceneDecorations'

export default function ResultScreen({ resultData, name, dinoName, answers, onPublish, onDone }) {
  const publishedRef = useRef(false)

  useEffect(() => {
    if (!publishedRef.current) {
      publishedRef.current = true
      onPublish(answers, name)
    }
  }, [onPublish, answers, name])

  const imgSrc = resultData?.image_b64
    ? `data:image/png;base64,${resultData.image_b64}`
    : null

  return (
    <div className="screen center">
      <SceneDecorations seed={7} />
      <h2>Portrettet ditt er klart!</h2>
      <p className="result-name">{name} — the {dinoName}</p>
      {imgSrc && (
        <img src={imgSrc} alt="Your pixel art portrait" className="result-image" />
      )}
      <p className="result-hint">Sjekk TV-veggen for å se deg selv!</p>
      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
