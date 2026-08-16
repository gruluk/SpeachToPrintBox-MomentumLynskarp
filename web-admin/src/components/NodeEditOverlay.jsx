import { useEffect, useState } from 'react'
import { ReorderList, ScreenPreview } from './ScreenPreviews'

const SCREEN_HELP = {
  start: 'Første side gjesten ser. Knappene «Registrer» og «Sjekk ut» følger pilene i canvas.',
  privacy: 'Samtykkeside før registrering. Endre teksten og se forhåndsvisningen til venstre.',
  name_input: 'Gjesten finner seg selv i listen — eller registrerer ny hvis walk-up er på.',
  interest_select: 'Temaene som trykkes på navneskiltet. Dra for å endre rekkefølge.',
  done: 'Bekreftelse etter registrering. Etiketten køes til printeren.',
  qr_scan: 'Utsjekk: skann QR på navneskiltet.',
  demo_matched: 'Spørsmål om demo etter skanning.',
  demo_done: 'Bekreftelse hvis de vil ha demo.',
  checkout_done: 'Bekreftelse hvis de ikke vil ha demo.',
}

export default function NodeEditOverlay({
  selected,
  event,
  onClose,
  onRemove,
  onSaveSettings,
  onSaveFlow,
}) {
  const screen = selected?.data?.screen
  const kind = selected?.data?.kind
  const [draft, setDraft] = useState(event)
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setDraft(event)
    setMsg('')
  }, [event, selected?.id])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function save(patch) {
    setSaving(true)
    setMsg('')
    try {
      await onSaveSettings(patch)
      setMsg('Lagret')
    } catch (e) {
      setMsg(e.message)
    } finally {
      setSaving(false)
    }
  }

  const title = selected?.data?.label || kind || screen || 'Node'
  const help = SCREEN_HELP[screen] || (kind === 'printer'
    ? 'Kobling til etikettprinteren. Når interesser er valgt, køes en utskrift.'
    : kind === 'attendees'
      ? 'Kobling til deltakerlisten for dette arrangementet.'
      : 'Denne noden er en del av booth-flyten.')

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel" onClick={(e) => e.stopPropagation()}>
        <header className="overlay-header">
          <div>
            <p className="overlay-kicker">{kind ? 'Integrasjon' : 'Booth-side'}</p>
            <h2>{title}</h2>
            <p className="muted overlay-help">{help}</p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Lukk
          </button>
        </header>

        <div className={`overlay-body${kind ? ' integration-only' : ''}`}>
          {!kind && (
            <div className="overlay-preview-col">
              <p className="overlay-preview-label">Forhåndsvisning (iPad)</p>
              <div className="phone-frame">
                <div className="phone-notch" />
                <div className="phone-screen">
                  <ScreenPreview screen={screen} event={event} draft={draft} />
                </div>
              </div>
            </div>
          )}

          <div className="overlay-editor-col">
            {kind === 'printer' && (
              <div className="stack">
                <p className="muted">
                  Etiketter køes automatisk når noen fullfører interessene. Kjør{' '}
                  <code>mac_print_client.py</code> på Macen som er koblet til Brother-printeren.
                </p>
              </div>
            )}

            {kind === 'attendees' && (
              <div className="stack">
                <p className="muted">
                  Navn-/telefonoppslag bruker listen under fanen «Deltakere». Importer Excel/CSV der.
                </p>
              </div>
            )}

            {screen === 'privacy' && (
              <div className="stack">
                <label className="field">
                  Overskrift
                  <input
                    className="input"
                    value={draft.privacy_title || ''}
                    onChange={(e) => setDraft({ ...draft, privacy_title: e.target.value })}
                  />
                </label>
                <div>
                  <p className="field-label">Punkter — dra ⠿ for å endre rekkefølge</p>
                  <ReorderList
                    items={draft.privacy_bullets || []}
                    onChange={(privacy_bullets) => setDraft({ ...draft, privacy_bullets })}
                    placeholder="Nytt punkt"
                    addLabel="Legg til punkt"
                  />
                </div>
                <label className="field">
                  Avkrysningstekst
                  <textarea
                    className="textarea"
                    value={draft.privacy_checkbox_label || ''}
                    onChange={(e) => setDraft({ ...draft, privacy_checkbox_label: e.target.value })}
                  />
                </label>
                <button
                  className="btn btn-primary"
                  disabled={saving}
                  onClick={() =>
                    save({
                      privacy_title: draft.privacy_title,
                      privacy_bullets: draft.privacy_bullets,
                      privacy_checkbox_label: draft.privacy_checkbox_label,
                    })
                  }
                >
                  Lagre personvern
                </button>
              </div>
            )}

            {screen === 'interest_select' && (
              <div className="stack">
                <div>
                  <p className="field-label">Interesser — dra ⠿ for å endre rekkefølge</p>
                  <ReorderList
                    items={draft.interests || []}
                    onChange={(interests) => setDraft({ ...draft, interests })}
                    placeholder="Ny interesse"
                    addLabel="Legg til interesse"
                  />
                </div>
                <label className="field">
                  Maks antall valg
                  <input
                    className="input"
                    type="number"
                    min={1}
                    max={10}
                    value={draft.max_interests || 3}
                    onChange={(e) => setDraft({ ...draft, max_interests: Number(e.target.value) })}
                  />
                </label>
                <button
                  className="btn btn-primary"
                  disabled={saving}
                  onClick={() =>
                    save({ interests: draft.interests, max_interests: draft.max_interests })
                  }
                >
                  Lagre interesser
                </button>
              </div>
            )}

            {screen === 'name_input' && (
              <div className="stack">
                <label className="field">
                  Hvordan finner gjesten seg selv?
                  <select
                    className="select"
                    value={draft.lookup_mode || 'name'}
                    onChange={(e) => setDraft({ ...draft, lookup_mode: e.target.value })}
                  >
                    <option value="name">Søk på navn</option>
                    <option value="phone">Søk på telefon</option>
                    <option value="both">Søk på navn eller telefon</option>
                  </select>
                </label>
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={Boolean(draft.allow_walkup_registration)}
                    onChange={(e) =>
                      setDraft({ ...draft, allow_walkup_registration: e.target.checked })
                    }
                  />
                  <span>
                    <strong>Tillat walk-up</strong>
                    <br />
                    <span className="muted">Gjest kan registrere seg hvis de ikke finnes i listen</span>
                  </span>
                </label>
                <button
                  className="btn btn-primary"
                  disabled={saving}
                  onClick={() =>
                    save({
                      lookup_mode: draft.lookup_mode,
                      allow_walkup_registration: draft.allow_walkup_registration,
                    })
                  }
                >
                  Lagre
                </button>
              </div>
            )}

            {screen === 'start' && (
              <div className="stack">
                <p className="muted">
                  Startskjermen styres av pilene i canvas: «register» går til registreringsflyten,
                  «checkout» til QR-utsjekk. Booth-modus (Begge / Kun registrering / Kun utsjekk)
                  settes under fanen Booths.
                </p>
                <button className="btn btn-primary" disabled={saving} onClick={() => onSaveFlow?.()}>
                  Lagre flyt
                </button>
              </div>
            )}

            {screen &&
              !['privacy', 'interest_select', 'name_input', 'start'].includes(screen) && (
                <div className="stack">
                  <p className="muted">
                    Denne siden har fast innhold. Du kan fjerne den fra flyten hvis du ikke trenger den.
                  </p>
                </div>
              )}

            <div className="overlay-footer">
              {selected?.id !== 'start' && (
                <button type="button" className="btn btn-ghost danger" onClick={onRemove}>
                  Fjern fra flyt
                </button>
              )}
              {msg && <span className="muted">{msg}</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
