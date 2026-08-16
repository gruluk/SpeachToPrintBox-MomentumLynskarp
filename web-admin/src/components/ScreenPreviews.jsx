import { useState } from 'react'

/** Live booth-style previews for the canvas editor. */
export function ScreenPreview({ screen, event, draft }) {
  const cfg = { ...event, ...draft }

  if (screen === 'privacy') {
    return (
      <div className="preview-screen">
        <h2 className="preview-title">{cfg.privacy_title || 'Personvern'}</h2>
        <div className="preview-card">
          <ul className="preview-bullets">
            {(cfg.privacy_bullets || []).map((b, i) => (
              <li key={`${i}-${b.slice(0, 12)}`}>{b}</li>
            ))}
          </ul>
        </div>
        <label className="preview-check">
          <span className="preview-checkbox" />
          <span>{cfg.privacy_checkbox_label || 'Jeg samtykker…'}</span>
        </label>
        <div className="preview-btns">
          <span className="preview-btn ghost">Avbryt</span>
          <span className="preview-btn primary">Neste</span>
        </div>
      </div>
    )
  }

  if (screen === 'interest_select') {
    const max = cfg.max_interests || 3
    const interests = cfg.interests || []
    return (
      <div className="preview-screen">
        <p className="preview-sub">Hyggelig å se deg, Ola!</p>
        <h2 className="preview-title">Velg dine interesseområder</h2>
        <p className="preview-muted">Velg 1–{max} temaer</p>
        <div className="preview-interest-grid">
          {interests.map((interest) => (
            <span key={interest} className="preview-chip">
              {interest}
            </span>
          ))}
          {interests.length === 0 && (
            <span className="preview-muted">Ingen interesser ennå — legg til til høyre</span>
          )}
        </div>
        <div className="preview-btns">
          <span className="preview-btn ghost">Avbryt</span>
          <span className="preview-btn primary">Neste</span>
        </div>
      </div>
    )
  }

  if (screen === 'name_input') {
    const mode = cfg.lookup_mode || 'name'
    const placeholder =
      mode === 'phone'
        ? 'Søk etter telefonnummer...'
        : mode === 'both'
          ? 'Søk etter navn eller telefon...'
          : 'Søk etter navnet ditt...'
    const title = mode === 'phone' ? 'Hva er telefonnummeret ditt?' : 'Hva heter du?'
    return (
      <div className="preview-screen">
        <h2 className="preview-title">{title}</h2>
        <div className="preview-input">{placeholder}</div>
        <div className="preview-list">
          <div className="preview-list-item">Ada Lovelace</div>
          <div className="preview-list-item selected">Ola Nordmann</div>
          <div className="preview-list-item">Kari Hansen</div>
        </div>
        {cfg.allow_walkup_registration ? (
          <p className="preview-muted">
            Finner du ikke navnet? <span className="preview-link">Registrer ny</span>
          </p>
        ) : (
          <p className="preview-muted">Finner du ikke navnet ditt? Ta kontakt med en av våre ansatte.</p>
        )}
        <div className="preview-btns">
          <span className="preview-btn ghost">Avbryt</span>
          <span className="preview-btn primary">Neste</span>
        </div>
      </div>
    )
  }

  if (screen === 'start') {
    return (
      <div className="preview-screen preview-start">
        <div className="preview-logo">Sopra Steria</div>
        <p className="preview-sub">Velkommen!</p>
        <div className="preview-btns col">
          <span className="preview-btn start">Registrer deg</span>
          <span className="preview-btn primary">Sjekk ut her</span>
        </div>
      </div>
    )
  }

  if (screen === 'done') {
    return (
      <div className="preview-screen preview-center">
        <h2 className="preview-title">Takk, Ola!</h2>
        <p className="preview-muted">Navneskiltet ditt skrives ut nå.</p>
        <span className="preview-btn primary">Ferdig</span>
      </div>
    )
  }

  if (screen === 'qr_scan') {
    return (
      <div className="preview-screen preview-center">
        <h2 className="preview-title">Skann QR-koden</h2>
        <div className="preview-qr-box" />
        <p className="preview-muted">Hold navneskiltet foran kameraet</p>
      </div>
    )
  }

  if (screen === 'demo_matched') {
    return (
      <div className="preview-screen preview-center">
        <h2 className="preview-title">Hei, Ola!</h2>
        <p className="preview-muted">Vil du ha en demo?</p>
        <div className="preview-btns">
          <span className="preview-btn ghost">Nei takk</span>
          <span className="preview-btn primary">Ja, gjerne</span>
        </div>
      </div>
    )
  }

  if (kindLabel(screen)) {
    return (
      <div className="preview-screen preview-center">
        <h2 className="preview-title">{kindLabel(screen)}</h2>
        <p className="preview-muted">Forhåndsvisning av denne siden.</p>
      </div>
    )
  }

  return (
    <div className="preview-screen preview-center">
      <p className="preview-muted">Ingen forhåndsvisning</p>
    </div>
  )
}

function kindLabel(screen) {
  const map = {
    demo_done: 'Demo ferdig',
    checkout_done: 'Utsjekk ferdig',
  }
  return map[screen] || null
}

/** Drag-reorderable list of strings with inline edit. */
export function ReorderList({ items, onChange, placeholder = 'Nytt punkt…', addLabel = 'Legg til' }) {
  const [dragIndex, setDragIndex] = useState(null)

  function move(from, to) {
    if (to < 0 || to >= items.length || from === to) return
    const next = [...items]
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    onChange(next)
  }

  function onDragStart(i) {
    setDragIndex(i)
  }

  function onDragOver(e, i) {
    e.preventDefault()
    if (dragIndex === null || dragIndex === i) return
    move(dragIndex, i)
    setDragIndex(i)
  }

  function onDragEnd() {
    setDragIndex(null)
  }

  return (
    <div className="reorder-list">
      {items.map((item, i) => (
        <div
          key={`row-${i}`}
          className={`reorder-row${dragIndex === i ? ' dragging' : ''}`}
          draggable
          onDragStart={() => onDragStart(i)}
          onDragOver={(e) => onDragOver(e, i)}
          onDragEnd={onDragEnd}
        >
          <span className="reorder-handle" title="Dra for å endre rekkefølge">
            ⠿
          </span>
          <input
            className="input"
            value={item}
            onChange={(e) => {
              const next = [...items]
              next[i] = e.target.value
              onChange(next)
            }}
          />
          <button
            type="button"
            className="btn btn-ghost reorder-remove"
            onClick={() => onChange(items.filter((_, j) => j !== i))}
            title="Fjern"
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn btn-ghost"
        onClick={() => onChange([...items, ''])}
      >
        + {addLabel}
      </button>
    </div>
  )
}
