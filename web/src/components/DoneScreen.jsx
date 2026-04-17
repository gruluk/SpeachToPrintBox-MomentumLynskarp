import { useState } from 'react'

export default function DoneScreen({ name, interest, userId, onDone }) {
  const [imageLoaded, setImageLoaded] = useState(false)

  const previewUrl = userId
    ? `/label-preview/${userId}?name=${encodeURIComponent(name)}&interest=${encodeURIComponent(interest)}`
    : null

  return (
    <div className="screen center done-screen">
      <h2>Registrering fullført!</h2>
      <p className="status-sub">Du er registrert. Etiketten din skrives ut.</p>

      {previewUrl && (
        <div className="printer-anim">
          <div className="printer-slot" />
          <div className={`printer-paper ${imageLoaded ? 'printing' : ''}`}>
            <div className="label-preview">
              <img
                src={previewUrl}
                alt="Etikett-forhåndsvisning"
                className="label-preview-img"
                onLoad={() => setImageLoaded(true)}
              />
            </div>
          </div>
        </div>
      )}

      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
