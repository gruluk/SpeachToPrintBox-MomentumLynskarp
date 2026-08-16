import { useEffect, useState } from 'react'
import { api } from '../api'

export default function AttendeesPanel({ event }) {
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')

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
    try {
      const res = await api.importUsers(event.id, file)
      alert(`Importert ${res.imported}, hoppet over ${res.skipped}`)
      await load()
    } catch (err) {
      setError(err.message)
    }
    e.target.value = ''
  }

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>Deltakere ({users.length})</h2>
        <div className="row">
          <a className="btn btn-ghost" href={`/admin/api/events/${event.id}/export-users`}>
            Eksporter
          </a>
          <a className="btn btn-ghost" href={`/admin/api/events/${event.id}/export-interests`}>
            Interesser
          </a>
          <label className="btn btn-ghost" style={{ cursor: 'pointer' }}>
            Importer
            <input type="file" accept=".csv,.xlsx" hidden onChange={onImport} />
          </label>
          <button
            className="btn btn-ghost"
            onClick={async () => {
              if (!confirm('Nullstill alle registreringer?')) return
              await api.clearRegistrations(event.id)
              await load()
            }}
          >
            Nullstill reg.
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
    </div>
  )
}
