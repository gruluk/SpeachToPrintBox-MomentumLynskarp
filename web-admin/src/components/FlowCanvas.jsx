import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useEdgesState,
  useNodesState,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

const DEFAULT_FLOW = {
  nodes: [
    { id: 'start', type: 'screen', position: { x: 80, y: 200 }, data: { screen: 'start', label: 'Start' } },
    { id: 'privacy', type: 'screen', position: { x: 320, y: 80 }, data: { screen: 'privacy', label: 'Personvern' } },
    { id: 'name', type: 'screen', position: { x: 560, y: 80 }, data: { screen: 'name_input', label: 'Navn' } },
    { id: 'interests', type: 'screen', position: { x: 800, y: 80 }, data: { screen: 'interest_select', label: 'Interesser' } },
    { id: 'done', type: 'screen', position: { x: 1040, y: 80 }, data: { screen: 'done', label: 'Ferdig' } },
    { id: 'qr', type: 'screen', position: { x: 320, y: 320 }, data: { screen: 'qr_scan', label: 'QR-skanning' } },
    { id: 'demo_matched', type: 'screen', position: { x: 560, y: 320 }, data: { screen: 'demo_matched', label: 'Demo' } },
    { id: 'demo_done', type: 'screen', position: { x: 800, y: 280 }, data: { screen: 'demo_done', label: 'Demo ferdig' } },
    { id: 'checkout_done', type: 'screen', position: { x: 800, y: 400 }, data: { screen: 'checkout_done', label: 'Utsjekk' } },
    { id: 'printer', type: 'integration', position: { x: 1040, y: 280 }, data: { kind: 'printer', label: 'Printer' } },
    { id: 'db', type: 'integration', position: { x: 80, y: 400 }, data: { kind: 'attendees', label: 'Deltakere' } },
  ],
  edges: [
    { id: 'e1', source: 'start', target: 'privacy', data: { action: 'register' } },
    { id: 'e2', source: 'privacy', target: 'name', data: { action: 'next' } },
    { id: 'e3', source: 'name', target: 'interests', data: { action: 'next' } },
    { id: 'e4', source: 'interests', target: 'done', data: { action: 'next' } },
    { id: 'e5', source: 'interests', target: 'printer', data: { action: 'print_label' } },
    { id: 'e6', source: 'start', target: 'qr', data: { action: 'checkout' } },
    { id: 'e7', source: 'qr', target: 'demo_matched', data: { action: 'next' } },
    { id: 'e8', source: 'demo_matched', target: 'demo_done', data: { action: 'wants_demo' } },
    { id: 'e9', source: 'demo_matched', target: 'checkout_done', data: { action: 'no_demo' } },
    { id: 'e10', source: 'name', target: 'db', data: { action: 'lookup' } },
  ],
}

function FlowNode({ data, selected }) {
  const isIntegration = data.kind
  return (
    <div className={`flow-node${isIntegration ? ' integration' : ''}${selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Left} />
      <div>{data.label || data.screen || data.kind}</div>
      <div className="muted" style={{ fontSize: '0.7rem', fontWeight: 500, marginTop: 2 }}>
        {isIntegration ? data.kind : data.screen}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

const nodeTypes = { screen: FlowNode, integration: FlowNode }

function toRfNodes(flow) {
  return (flow?.nodes || []).map((n) => ({
    id: n.id,
    type: n.type === 'integration' ? 'integration' : 'screen',
    position: n.position || { x: 0, y: 0 },
    data: { ...n.data },
  }))
}

function toRfEdges(flow) {
  return (flow?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.data?.action || '',
    markerEnd: { type: MarkerType.ArrowClosed },
    data: e.data || {},
  }))
}

function fromRf(nodes, edges) {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type === 'integration' ? 'integration' : 'screen',
      position: n.position,
      data: n.data,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      data: e.data || { action: e.label || 'next' },
    })),
  }
}

export default function FlowCanvas({ event, onSaveFlow, onSaveSettings }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const flow = event.flow?.nodes ? event.flow : DEFAULT_FLOW
    setNodes(toRfNodes(flow))
    setEdges(toRfEdges(flow))
  }, [event.id, event.flow, setNodes, setEdges])

  const onSelectionChange = useCallback(({ nodes: sel }) => {
    setSelected(sel[0] || null)
  }, [])

  async function save() {
    setSaving(true)
    setMessage('')
    try {
      await onSaveFlow(fromRf(nodes, edges))
      setMessage('Lagret')
    } catch (e) {
      setMessage(e.message)
    } finally {
      setSaving(false)
    }
  }

  function resetFlow() {
    if (!confirm('Tilbakestill til standard flyt?')) return
    setNodes(toRfNodes(DEFAULT_FLOW))
    setEdges(toRfEdges(DEFAULT_FLOW))
  }

  function removeSelected() {
    if (!selected) return
    if (selected.id === 'start') {
      alert('Start-noden kan ikke slettes')
      return
    }
    if (!confirm(`Fjern «${selected.data?.label || selected.id}» fra flyten?`)) return
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
  }

  const side = useMemo(() => {
    if (!selected) {
      return (
        <div className="stack">
          <h3>Canvas</h3>
          <p className="muted">
            Velg en side for å redigere innstillinger. Slett en side for å hoppe over den i booth-flyten.
            Lagre når du er ferdig.
          </p>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            Lagre flyt
          </button>
          <button className="btn btn-ghost" onClick={resetFlow}>
            Tilbakestill flyt
          </button>
          {message && <p className="muted">{message}</p>}
        </div>
      )
    }

    const screen = selected.data?.screen
    const kind = selected.data?.kind

    return (
      <NodeEditor
        selected={selected}
        event={event}
        screen={screen}
        kind={kind}
        onRemove={removeSelected}
        onSaveSettings={onSaveSettings}
        onSaveFlow={async () => {
          await onSaveFlow(fromRf(nodes, edges))
        }}
      />
    )
  }, [selected, event, nodes, edges, saving, message])

  return (
    <div className="canvas-wrap">
      <div className="canvas-main">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onSelectionChange={onSelectionChange}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
        >
          <Background gap={18} color="#3a1a55" />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </div>
      <aside className="canvas-side">{side}</aside>
    </div>
  )
}

function NodeEditor({ selected, event, screen, kind, onRemove, onSaveSettings }) {
  const [local, setLocal] = useState(event)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    setLocal(event)
  }, [event])

  async function saveSettings(patch) {
    setMsg('')
    try {
      await onSaveSettings(patch)
      setMsg('Lagret')
    } catch (e) {
      setMsg(e.message)
    }
  }

  if (kind === 'printer') {
    return (
      <div className="stack">
        <h3>Printer</h3>
        <p className="muted">
          Etiketter køes når deltakeren velger interesser. mac_print_client henter jobber med
          label_printed=false for dette arrangementet.
        </p>
        <button className="btn btn-ghost" onClick={onRemove}>
          Skjul node
        </button>
      </div>
    )
  }

  if (kind === 'attendees') {
    return (
      <div className="stack">
        <h3>Deltakere</h3>
        <p className="muted">Oppslag mot arrangementets deltakerliste (navn/telefon).</p>
        <button className="btn btn-ghost" onClick={onRemove}>
          Skjul node
        </button>
      </div>
    )
  }

  if (screen === 'privacy') {
    return (
      <div className="stack">
        <h3>Personvern</h3>
        <label className="field">
          Tittel
          <input
            className="input"
            value={local.privacy_title || ''}
            onChange={(e) => setLocal({ ...local, privacy_title: e.target.value })}
          />
        </label>
        <label className="field">
          Punkter (én per linje)
          <textarea
            className="textarea"
            value={(local.privacy_bullets || []).join('\n')}
            onChange={(e) =>
              setLocal({
                ...local,
                privacy_bullets: e.target.value.split('\n').filter((l) => l.trim()),
              })
            }
          />
        </label>
        <label className="field">
          Avkrysningstekst
          <textarea
            className="textarea"
            value={local.privacy_checkbox_label || ''}
            onChange={(e) => setLocal({ ...local, privacy_checkbox_label: e.target.value })}
          />
        </label>
        <button
          className="btn btn-primary"
          onClick={() =>
            saveSettings({
              privacy_title: local.privacy_title,
              privacy_bullets: local.privacy_bullets,
              privacy_checkbox_label: local.privacy_checkbox_label,
            })
          }
        >
          Lagre personvern
        </button>
        <button className="btn btn-ghost" onClick={onRemove}>
          Fjern side fra flyt
        </button>
        {msg && <p className="muted">{msg}</p>}
      </div>
    )
  }

  if (screen === 'interest_select') {
    return (
      <div className="stack">
        <h3>Interesser</h3>
        <label className="field">
          Interesseområder (én per linje)
          <textarea
            className="textarea"
            value={(local.interests || []).join('\n')}
            onChange={(e) =>
              setLocal({
                ...local,
                interests: e.target.value.split('\n').map((l) => l.trim()).filter(Boolean),
              })
            }
          />
        </label>
        <label className="field">
          Maks antall
          <input
            className="input"
            type="number"
            min={1}
            max={10}
            value={local.max_interests || 3}
            onChange={(e) => setLocal({ ...local, max_interests: Number(e.target.value) })}
          />
        </label>
        <button
          className="btn btn-primary"
          onClick={() =>
            saveSettings({ interests: local.interests, max_interests: local.max_interests })
          }
        >
          Lagre interesser
        </button>
        <button className="btn btn-ghost" onClick={onRemove}>
          Fjern side fra flyt
        </button>
        {msg && <p className="muted">{msg}</p>}
      </div>
    )
  }

  if (screen === 'name_input') {
    return (
      <div className="stack">
        <h3>Navn / oppslag</h3>
        <label className="field">
          Oppslagsmodus
          <select
            className="select"
            value={local.lookup_mode || 'name'}
            onChange={(e) => setLocal({ ...local, lookup_mode: e.target.value })}
          >
            <option value="name">Kun navn</option>
            <option value="phone">Kun telefon</option>
            <option value="both">Navn og telefon</option>
          </select>
        </label>
        <label className="field" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            checked={Boolean(local.allow_walkup_registration)}
            onChange={(e) => setLocal({ ...local, allow_walkup_registration: e.target.checked })}
          />
          Tillat registrering av ny deltaker på booth
        </label>
        <button
          className="btn btn-primary"
          onClick={() =>
            saveSettings({
              lookup_mode: local.lookup_mode,
              allow_walkup_registration: local.allow_walkup_registration,
            })
          }
        >
          Lagre
        </button>
        <button className="btn btn-ghost" onClick={onRemove}>
          Fjern side fra flyt
        </button>
        {msg && <p className="muted">{msg}</p>}
      </div>
    )
  }

  return (
    <div className="stack">
      <h3>{selected.data?.label || selected.id}</h3>
      <p className="muted">Skjerm: {screen || '—'}</p>
      {selected.id !== 'start' && (
        <button className="btn btn-ghost" onClick={onRemove}>
          Fjern side fra flyt
        </button>
      )}
    </div>
  )
}
