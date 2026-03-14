import SceneDecorations from './SceneDecorations'

export default function InfoScreen({ onContinue }) {
  return (
    <div className="screen center">
      <SceneDecorations seed={8} />
      <h2 className="info-title">🔒 Personverninformasjon</h2>
      <p className="info-body">
        Bildet ditt behandles av OpenAI gpt-image-1<br />
        for å lage en piksel-avatar av deg.
      </p>
      <p className="info-body">
        Selve bildet lagres ikke, kun avataren din<br />
        lagres midlertidig under arrangementet.
      </p>
      <button className="btn-start" onClick={onContinue}>
        Forstått, la oss starte! →
      </button>
    </div>
  )
}
