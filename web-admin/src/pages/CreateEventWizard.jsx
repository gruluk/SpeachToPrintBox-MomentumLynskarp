import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { emptyStartFlow } from '../flowCatalog'
import { joinStartsAt } from '../datetime'
import { ScreenPreview } from '../components/ScreenPreviews'

const STEPS = ['basics', 'welcome']

export default function CreateEventWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [answers, setAnswers] = useState({
    name: '',
    startDate: '',
    startTime: '',
  })

  const stepId = STEPS[step]
  const progress = ((step + 1) / STEPS.length) * 100

  function patch(p) {
    setAnswers((a) => ({ ...a, ...p }))
  }

  async function finish() {
    if (!answers.name.trim()) {
      setError('Gi arrangementet et navn')
      setStep(0)
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const created = await api.createEvent({
        name: answers.name.trim(),
        starts_at: joinStartsAt(answers.startDate, answers.startTime),
        ends_at: '',
        flow: emptyStartFlow(),
      })
      navigate(`/events/${created.id}`, { state: { guide: true } })
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
          {stepId === 'basics' && (
            <StepShell
              title="Hva heter arrangementet?"
              subtitle="Deretter starter vi med velkomstsiden og bygger flyten steg for steg."
            >
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
                  Dato (valgfritt)
                  <input
                    className="input"
                    type="date"
                    value={answers.startDate}
                    onChange={(e) => patch({ startDate: e.target.value })}
                  />
                </label>
                <label className="field" style={{ flex: 1 }}>
                  Starttid (valgfritt)
                  <input
                    className="input"
                    type="time"
                    value={answers.startTime}
                    onChange={(e) => patch({ startTime: e.target.value })}
                  />
                </label>
              </div>
            </StepShell>
          )}

          {stepId === 'welcome' && (
            <StepShell
              title="Velkomstsiden er startpunktet"
              subtitle="Dette er det første gjesten ser. Du kan klikke på den i canvas for å se forklaring. Neste steg foreslås etterpå — én side eller modul om gangen."
            >
              <div className="wizard-split">
                <div className="stack">
                  <div className="wizard-info-card">
                    <strong>Bygg nedenfra</strong>
                    <p className="muted">
                      Vi starter kun med Start. Du legger til sider og moduler etter hvert — for eksempel
                      Deltakere før Navneoppslag.
                    </p>
                  </div>
                  <div className="wizard-info-card">
                    <strong>Avhengigheter</strong>
                    <p className="muted">
                      Canvas blokkerer sider som trenger noe du ikke har lagt til ennå. Bruk + for å se
                      hva som er tilgjengelig.
                    </p>
                  </div>
                </div>
                <div className="wizard-preview">
                  <p className="overlay-preview-label">Forhåndsvisning — Start</p>
                  <div className="phone-frame compact">
                    <div className="phone-notch" />
                    <div className="phone-screen">
                      <ScreenPreview screen="start" event={{}} draft={{}} />
                    </div>
                  </div>
                </div>
              </div>
            </StepShell>
          )}

          {error && <p style={{ color: '#ff9aa8', marginTop: '1rem' }}>{error}</p>}

          <div className="wizard-nav">
            {step > 0 ? (
              <button type="button" className="btn btn-ghost" onClick={() => { setError(''); setStep(step - 1) }}>
                Tilbake
              </button>
            ) : (
              <span />
            )}
            {stepId === 'basics' ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  if (!answers.name.trim()) {
                    setError('Skriv inn et navn for arrangementet')
                    return
                  }
                  setError('')
                  setStep(1)
                }}
              >
                Neste — se velkomstside
              </button>
            ) : (
              <button type="button" className="btn btn-primary" disabled={submitting} onClick={finish}>
                {submitting ? 'Oppretter…' : 'Opprett og åpne canvas'}
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
