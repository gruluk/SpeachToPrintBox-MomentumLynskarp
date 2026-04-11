import { useEffect, useRef } from 'react'

export default function ResultScreen({ resultData, name, interest, onPublish, onDone }) {
  const publishedRef = useRef(false)

  useEffect(() => {
    if (!publishedRef.current) {
      publishedRef.current = true
      onPublish(name, interest)
    }
  }, [onPublish, name, interest])

  const imgSrc = resultData?.image_b64
    ? `data:image/png;base64,${resultData.image_b64}`
    : null

  return (
    <div className="screen center">
      <h2>Portrettet ditt er klart!</h2>
      <p className="result-name">{name}</p>
      {interest && <p className="result-interest">{interest}</p>}
      {imgSrc && (
        <img src={imgSrc} alt="Ditt pikselkunst-portrett" className="result-image" />
      )}
      <p className="result-hint">Sjekk skjermen for å se deg selv!</p>
      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
