import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { boothModeFromAnswers, buildFlowFromAnswers } from '../buildFlow'
import { ScreenPreview } from '../components/ScreenPreviews'

const DEFAULT_PRIVACY_BULLETS = [
  'Vi lagrer navn, epost, telefonnummer og valgte interesseområder for å administrere din deltakelse.',
  'Opplysningene brukes til å bekrefte registrering, lage navneskilt og eventuell oppfølging etter arrangementet.',
  'Du kan når som helst trekke samtykke tilbake ved å kontakte oss.',
  'All data slettes senest 90 dager etter at arrangementet er avsluttet.',
]

const STEPS = [
  'welcome',
  'basics',
  'purpose',
  'lookup',
  'privacy',
  'interests',
  'booths',
  'summary',
]

export default function CreateEventWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [answers, setAnswers] = useState({
    name: '',
    starts_at: '',
    ends_at: '',
    includeRegister: true,
    includeCheckout: true,
    includePrivacy: true,
    includeInterests: true,
    includePrinter: true,
    lookup_mode: 'name',
    allow_walkup_registration: false,
    privacy_title: 'Samtykke til bruk av dine opplysninger',
    privacy_bullets: [...DEFAULT_PRIVACY_BULLETS],
    privacy_checkbox_label:
      'Jeg samtykker til at Sopra Steria lagrer og behandler opplysningene mine slik det er beskrevet over.',
    interestsText: 'Økonomi\nRapportering\nKI i praksis\nEffektivisering',
    max_interests: 3,
    boothCount: 1,
  })

  const stepId = STEPS[step]
  const progress = ((step + 1) / STEPS.length) * 100

  function canShow(id) {
    if ((id === 'lookup' || id === 'interests' || id === 'privacy') && !answers.includeRegister) {
      return false
    }
    return true
  }

  function goNext() {
    setError('')
    let i = step + 1
    while (i < STEPS.length && !canShow(STEPS[i])) i += 1
    if (i >= STEPS.length) return
    // Special: privacy step asks includePrivacy — always show if register
    setStep(i)
  }

  function goBack() {
    setError('')
    let i = step - 1
    while (i >= 0 && !canShow(STEPS[i])) i -= 1
    if (i < 0) return
    setStep(i)
  }

  function patch(p) {
    setAnswers((a) => ({ ...a, ...p }))
  }

  const previewDraft = {
    privacy_title: answers.privacy_title,
    privacy_bullets: answers.privacy_bullets,
    privacy_checkbox_label: answers.privacy_checkbox_label,
    interests: answers.interestsText
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean),
    max_interests: answers.max_interests,
    lookup_mode: answers.lookup_mode,
    allow_walkup_registration: answers.allow_walkup_registration,
  }

  async function finish() {
    if (!answers.name.trim()) {
      setError('Gi arrangementet et navn')
      setStep(STEPS.indexOf('basics'))
      return
    }
    if (!answers.includeRegister && !answers.includeCheckout) {
      setError('Velg minst én funksjon: registrering eller utsjekk')
      setStep(STEPS.indexOf('purpose'))
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const interests = answers.interestsText
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean)
      const flow = buildFlowFromAnswers({
        includeRegister: answers.includeRegister,
        includeCheckout: answers.includeCheckout,
        includePrivacy: answers.includeRegister && answers.includePrivacy,
        includeInterests: answers.includeRegister && answers.includeInterests,
        includePrinter: answers.includeRegister && answers.includePrinter,
      })
      const mode = boothModeFromAnswers(answers)
      const created = await api.createEvent({
        name: answers.name.trim(),
        starts_at: answers.starts_at,
        ends_at: answers.ends_at,
        lookup_mode: answers.lookup_mode,
        allow_walkup_registration: answers.allow_walkup_registration,
        privacy_title: answers.privacy_title,
        privacy_bullets: answers.privacy_bullets,
        privacy_checkbox_label: answers.privacy_checkbox_label,
        interests: answers.includeInterests ? interests : [],
        max_interests: answers.max_interests,
        flow,
      })

      // Extra booths beyond the default one created by API
      const targetBooths = Math.max(1, Number(answers.boothCount) || 1)
      for (let i = 1; i < targetBooths; i += 1) {
        await api.createBooth(created.id)
      }
      // Set mode on all booths
      const booths = await api.listBooths(created.id)
      await Promise.all(booths.map((b) => api.patchBooth(created.id, b.id, { mode })))

      navigate(`/events/${created.id}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="row">
          <Link to="/" className="btn btn-ghost">
            ← Avbryt
          </Link>
          <h1>Nytt arrangement</h1>
        </div>
        <span className="muted">
          Steg {step + 1} av {STEPS.length}
        </span>
      </header>

      <div className="wizard-progress">
        <div className="wizard-progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <main className="content wizard-content">
        <div className="wizard-card">
          {stepId === 'welcome' && (
            <StepShell
              title="La oss bygge arrangementet ditt"
              subtitle="Vi går gjennom noen spørsmål, så setter vi opp booth-flyten automatisk. Du kan alltid endre alt i canvas etterpå."
            >
              <div className="wizard-choices">
                <div className="wizard-info-card">
                  <strong>Du velger</strong>
                  <p className="muted">Hva booth skal gjøre, hvordan folk finnes, personvern, interesser og antall iPads.</p>
                </div>
                <div className="wizard-info-card">
                  <strong>Vi bygger</strong>
                  <p className="muted">En ferdig flyt med sider og koblinger — klar til å åpne på canvas.</p>
                </div>
              </div>
            </StepShell>
          )}

          {stepId === 'basics' && (
            <StepShell title="Hva heter arrangementet?" subtitle="Dette vises for admin. URL-en lages automatisk fra navnet.">
              <label className="field">
                Navn
                <input
                  className="input"
                  autoFocus
                  placeholder="f.eks. Momentum Lynskarp Oslo"
                  value={answers.name}
                  onChange={(e) => patch({ name: e.target.value })}
                />
              </label>
              <div className="row">
                <label className="field" style={{ flex: 1 }}>
                  Startdato (valgfritt)
                  <input
                    className="input"
                    type="date"
                    value={answers.starts_at}
                    onChange={(e) => patch({ starts_at: e.target.value })}
                  />
                </label>
                <label className="field" style={{ flex: 1 }}>
                  Sluttdato (valgfritt)
                  <input
                    className="input"
                    type="date"
                    value={answers.ends_at}
                    onChange={(e) => patch({ ends_at: e.target.value })}
                  />
                </label>
              </div>
            </StepShell>
          )}

          {stepId === 'purpose' && (
            <StepShell
              title="Hva skal boothene gjøre?"
              subtitle="Du kan velge én eller begge. Dette styrer hvilke knapper gjesten ser på startsiden."
            >
              <label className={`wizard-option${answers.includeRegister ? ' on' : ''}`}>
                <input
                  type="checkbox"
                  checked={answers.includeRegister}
                  onChange={(e) => patch({ includeRegister: e.target.checked })}
                />
                <span>
                  <strong>Registrering</strong>
                  <br />
                  <span className="muted">Gjest finner seg selv, velger interesser, får navneskilt</span>
                </span>
              </label>
              <label className={`wizard-option${answers.includeCheckout ? ' on' : ''}`}>
                <input
                  type="checkbox"
                  checked={answers.includeCheckout}
                  onChange={(e) => patch({ includeCheckout: e.target.checked })}
                />
                <span>
                  <strong>Utsjekk / demo</strong>
                  <br />
                  <span className="muted">Skann QR på skiltet og spør om demo</span>
                </span>
              </label>
            </StepShell>
          )}

          {stepId === 'lookup' && (
            <StepShell
              title="Hvordan finner gjesten seg selv?"
              subtitle="Listen importeres senere under Deltakere. Her velger du søkefelt."
            >
              <div className="wizard-split">
                <div className="stack">
                  {[
                    { value: 'name', label: 'Kun navn', desc: 'Vanligst for konferanser' },
                    { value: 'phone', label: 'Kun telefon', desc: 'Bra hvis listen har mobilnummer' },
                    { value: 'both', label: 'Navn eller telefon', desc: 'Mest fleksibelt' },
                  ].map((opt) => (
                    <label key={opt.value} className={`wizard-option${answers.lookup_mode === opt.value ? ' on' : ''}`}>
                      <input
                        type="radio"
                        name="lookup"
                        checked={answers.lookup_mode === opt.value}
                        onChange={() => patch({ lookup_mode: opt.value })}
                      />
                      <span>
                        <strong>{opt.label}</strong>
                        <br />
                        <span className="muted">{opt.desc}</span>
                      </span>
                    </label>
                  ))}
                  <label className={`wizard-option${answers.allow_walkup_registration ? ' on' : ''}`}>
                    <input
                      type="checkbox"
                      checked={answers.allow_walkup_registration}
                      onChange={(e) => patch({ allow_walkup_registration: e.target.checked })}
                    />
                    <span>
                      <strong>Tillat walk-up registrering</strong>
                      <br />
                      <span className="muted">Hvis de ikke finnes i listen, kan de registrere seg på booth</span>
                    </span>
                  </label>
                </div>
                <div className="wizard-preview">
                  <p className="overlay-preview-label">Forhåndsvisning</p>
                  <div className="phone-frame compact">
                    <div className="phone-notch" />
                    <div className="phone-screen">
                      <ScreenPreview screen="name_input" event={{}} draft={previewDraft} />
                    </div>
                  </div>
                </div>
              </div>
            </StepShell>
          )}

          {stepId === 'privacy' && (
            <StepShell
              title="Trenger dere personvern-samtykke?"
              subtitle="Anbefalt når dere lagrer personopplysninger. Teksten kan endres senere."
            >
              <label className={`wizard-option${answers.includePrivacy ? ' on' : ''}`}>
                <input
                  type="radio"
                  name="privacy"
                  checked={answers.includePrivacy}
                  onChange={() => patch({ includePrivacy: true })}
                />
                <span>
                  <strong>Ja — vis samtykkeside</strong>
                  <br />
                  <span className="muted">Gjest må krysse av før de fortsetter</span>
                </span>
              </label>
              <label className={`wizard-option${!answers.includePrivacy ? ' on' : ''}`}>
                <input
                  type="radio"
                  name="privacy"
                  checked={!answers.includePrivacy}
                  onChange={() => patch({ includePrivacy: false })}
                />
                <span>
                  <strong>Nei — hopp over</strong>
                  <br />
                  <span className="muted">Går rett til navneoppslag</span>
                </span>
              </label>
              {answers.includePrivacy && (
                <div className="wizard-split" style={{ marginTop: '1rem' }}>
                  <div className="stack">
                    <label className="field">
                      Overskrift
                      <input
                        className="input"
                        value={answers.privacy_title}
                        onChange={(e) => patch({ privacy_title: e.target.value })}
                      />
                    </label>
                    <label className="field">
                      Punkter (én per linje)
                      <textarea
                        className="textarea"
                        rows={6}
                        value={answers.privacy_bullets.join('\n')}
                        onChange={(e) =>
                          patch({
                            privacy_bullets: e.target.value.split('\n').filter((l) => l.trim()),
                          })
                        }
                      />
                    </label>
                  </div>
                  <div className="wizard-preview">
                    <p className="overlay-preview-label">Forhåndsvisning</p>
                    <div className="phone-frame compact">
                      <div className="phone-notch" />
                      <div className="phone-screen">
                        <ScreenPreview screen="privacy" event={{}} draft={previewDraft} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </StepShell>
          )}

          {stepId === 'interests' && (
            <StepShell
              title="Interesseområder"
              subtitle="Disse trykkes på navneskiltet. Én interesse per linje."
            >
              <label className={`wizard-option${answers.includeInterests ? ' on' : ''}`}>
                <input
                  type="checkbox"
                  checked={answers.includeInterests}
                  onChange={(e) => patch({ includeInterests: e.target.checked, includePrinter: e.target.checked })}
                />
                <span>
                  <strong>Inkluder interessesteg</strong>
                  <br />
                  <span className="muted">Uten dette hopper flyten fra navn til ferdig</span>
                </span>
              </label>
              {answers.includeInterests && (
                <div className="wizard-split">
                  <div className="stack">
                    <label className="field">
                      Interesser
                      <textarea
                        className="textarea"
                        rows={8}
                        value={answers.interestsText}
                        onChange={(e) => patch({ interestsText: e.target.value })}
                      />
                    </label>
                    <label className="field">
                      Maks antall valg
                      <input
                        className="input"
                        type="number"
                        min={1}
                        max={10}
                        value={answers.max_interests}
                        onChange={(e) => patch({ max_interests: Number(e.target.value) })}
                      />
                    </label>
                    <label className={`wizard-option${answers.includePrinter ? ' on' : ''}`}>
                      <input
                        type="checkbox"
                        checked={answers.includePrinter}
                        onChange={(e) => patch({ includePrinter: e.target.checked })}
                      />
                      <span>
                        <strong>Koble til printer</strong>
                        <br />
                        <span className="muted">Kø etikett når interesser er valgt</span>
                      </span>
                    </label>
                  </div>
                  <div className="wizard-preview">
                    <p className="overlay-preview-label">Forhåndsvisning</p>
                    <div className="phone-frame compact">
                      <div className="phone-notch" />
                      <div className="phone-screen">
                        <ScreenPreview screen="interest_select" event={{}} draft={previewDraft} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </StepShell>
          )}

          {stepId === 'booths' && (
            <StepShell
              title="Hvor mange booths (iPads)?"
              subtitle="Hver booth får sin egen URL. Du kan legge til flere senere."
            >
              <div className="wizard-booth-picker">
                {[1, 2, 3, 4].map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`wizard-booth-btn${answers.boothCount === n ? ' on' : ''}`}
                    onClick={() => patch({ boothCount: n })}
                  >
                    {n}
                  </button>
                ))}
                <label className="field" style={{ margin: 0, minWidth: 100 }}>
                  Annet
                  <input
                    className="input"
                    type="number"
                    min={1}
                    max={20}
                    value={answers.boothCount}
                    onChange={(e) => patch({ boothCount: Math.max(1, Number(e.target.value) || 1) })}
                  />
                </label>
              </div>
            </StepShell>
          )}

          {stepId === 'summary' && (
            <StepShell title="Klar til å opprette" subtitle="Sjekk oppsummeringen. Du kan finjustere i canvas etterpå.">
              <ul className="wizard-summary">
                <li>
                  <strong>Navn:</strong> {answers.name || '—'}
                </li>
                <li>
                  <strong>Funksjoner:</strong>{' '}
                  {[
                    answers.includeRegister && 'Registrering',
                    answers.includeCheckout && 'Utsjekk/demo',
                  ]
                    .filter(Boolean)
                    .join(', ') || '—'}
                </li>
                {answers.includeRegister && (
                  <>
                    <li>
                      <strong>Oppslag:</strong> {answers.lookup_mode}
                      {answers.allow_walkup_registration ? ' + walk-up' : ''}
                    </li>
                    <li>
                      <strong>Personvern:</strong> {answers.includePrivacy ? 'Ja' : 'Nei'}
                    </li>
                    <li>
                      <strong>Interesser:</strong>{' '}
                      {answers.includeInterests
                        ? `${previewDraft.interests.length} stk (maks ${answers.max_interests})`
                        : 'Nei'}
                    </li>
                    <li>
                      <strong>Printer:</strong> {answers.includePrinter && answers.includeInterests ? 'Ja' : 'Nei'}
                    </li>
                  </>
                )}
                <li>
                  <strong>Booths:</strong> {answers.boothCount}
                </li>
              </ul>
            </StepShell>
          )}

          {error && <p style={{ color: '#ff9aa8', marginTop: '1rem' }}>{error}</p>}

          <div className="wizard-nav">
            {step > 0 ? (
              <button type="button" className="btn btn-ghost" onClick={goBack}>
                Tilbake
              </button>
            ) : (
              <span />
            )}
            {stepId !== 'summary' ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  if (stepId === 'basics' && !answers.name.trim()) {
                    setError('Skriv inn et navn for arrangementet')
                    return
                  }
                  if (
                    stepId === 'purpose' &&
                    !answers.includeRegister &&
                    !answers.includeCheckout
                  ) {
                    setError('Velg minst én funksjon')
                    return
                  }
                  goNext()
                }}
              >
                Neste
              </button>
            ) : (
              <button type="button" className="btn btn-primary" disabled={submitting} onClick={finish}>
                {submitting ? 'Oppretter…' : 'Opprett arrangement'}
              </button>
            )}
          </div>
        </div>
      </main>
    </>
  )
}

function StepShell({ title, subtitle, children }) {
  return (
    <div className="stack">
      <div>
        <h2 className="wizard-title">{title}</h2>
        {subtitle && <p className="muted wizard-sub">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}
