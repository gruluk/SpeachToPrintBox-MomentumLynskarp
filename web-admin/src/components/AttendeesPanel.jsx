import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const IMPORT_TEMPLATE_CSV = `name,email,phone
Ada Lovelace,ada@example.com,+4712345678
Ola Nordmann,ola@example.com,90012345
Kari Hansen,,92011122
`

function downloadTemplate() {
  const blob = new Blob([IMPORT_TEMPLATE_CSV], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'deltakere-mal.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function AttendeesPanel({ event }) {
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [importOpen, setImportOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const fileRef = useRef(null)

  async function load() {
    try {
      setUsers(await api.listUsers(event.id))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [event.id])

  async function addUser(e) {
    e.preventDefault()
    try {
      await api.addUser(event.id, { name, email, phone })
      setName('')
      setEmail('')
      setPhone('')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function onImport(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    setError('')
    try {
      const res = await api.importUsers(event.id, file)
      alert(`Importert ${res.imported}, hoppet over ${res.skipped}`)
      setImportOpen(false)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Deltakere ({users.length})</h2>
          <p className="muted" style={{ marginTop: '0.35rem', maxWidth: 420 }}>
            Listen booth bruker til navneoppslag. Last ned for backup, eller last opp en CSV/Excel for å fylle
            listen.
          </p>
        </div>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={async () => {
            if (!confirm('Nullstill alle registreringer?')) return
            await api.clearRegistrations(event.id)
            await load()
          }}
        >
          Nullstill reg.
        </button>
      </div>

      <div className="attendee-actions">
        <div className="attendee-action-group">
          <p className="attendee-action-label">Last ned ↓</p>
          <div className="row">
            <a
              className="btn btn-ghost"
              href={`/admin/api/events/${event.id}/export-users`}
              download
              title="Last ned Excel med alle deltakere"
            >
              ↓ Deltakerliste
            </a>
            <a
              className="btn btn-ghost"
              href={`/admin/api/events/${event.id}/export-interests`}
              download
              title="Last ned Excel med valgte interesser"
            >
              ↓ Interesser
            </a>
          </div>
        </div>

        <div className="attendee-action-group upload">
          <p className="attendee-action-label">Last opp ↑</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setImportOpen(true)}
          >
            ↑ Importer deltakere
          </button>
        </div>
      </div>

      {error && <p style={{ color: '#ff9aa8' }}>{error}</p>}

      <form className="card row" onSubmit={addUser}>
        <input className="input" placeholder="Navn" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" placeholder="E-post" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="input" placeholder="Telefon" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button className="btn btn-primary">Legg til</button>
      </form>

      <div className="card" style={{ overflow: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>Navn</th>
              <th>E-post</th>
              <th>Telefon</th>
              <th>Interesser</th>
              <th>Kode</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.phone}</td>
                <td>{u.interest}</td>
                <td>{u.short_code}</td>
                <td>
                  <button
                    className="btn btn-ghost"
                    type="button"
                    onClick={async () => {
                      if (!confirm(`Slette ${u.name}?`)) return
                      await api.deleteUser(event.id, u.id)
                      await load()
                    }}
                  >
                    Slett
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {importOpen && (
        <div className="import-backdrop" onClick={() => !importing && setImportOpen(false)}>
          <div className="import-panel" onClick={(e) => e.stopPropagation()}>
            <header className="import-panel-header">
              <div>
                <h3>Importer deltakere</h3>
                <p className="muted">Last opp en CSV eller Excel-fil. Kolonnene må hete som under.</p>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={importing}
                onClick={() => setImportOpen(false)}
              >
                Lukk
              </button>
            </header>

            <div className="import-format card" style={{ marginBottom: '1rem' }}>
              <p className="field-label">Påkrevd format</p>
              <p className="muted" style={{ marginBottom: '0.65rem', fontSize: '0.88rem' }}>
                Første rad = overskrifter. <strong>name</strong> (eller navn) er påkrevd. E-post og telefon er
                valgfritt. Norske navn som <code>navn</code>, <code>epost</code>, <code>telefon</code> fungerer
                også.
              </p>
              <pre className="import-sample">{IMPORT_TEMPLATE_CSV.trim()}</pre>
              <button type="button" className="btn btn-ghost" onClick={downloadTemplate}>
                ↓ Last ned mal (CSV)
              </button>
            </div>

            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              hidden
              onChange={onImport}
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={importing}
              onClick={() => fileRef.current?.click()}
            >
              {importing ? 'Importerer…' : '↑ Velg fil og last opp'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
