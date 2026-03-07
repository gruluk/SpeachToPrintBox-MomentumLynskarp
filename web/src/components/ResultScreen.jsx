import { useEffect, useRef } from 'react'

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
      <h2>Your portrait is ready!</h2>
      <p className="result-name">{name} — the {dinoName}</p>
      {imgSrc && (
        <img src={imgSrc} alt="Your pixel art portrait" className="result-image" />
      )}
      <p className="result-hint">Check the TV wall to see yourself!</p>
      <button className="btn-primary" onClick={onDone}>Done</button>
    </div>
  )
}
