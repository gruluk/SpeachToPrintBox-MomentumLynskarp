import { useCallback, useEffect, useState } from 'react'
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
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import NodeEditOverlay from './NodeEditOverlay'

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

const NODE_ICONS = {
  start: '🏠',
  privacy: '🔒',
  name_input: '👤',
  interest_select: '✨',
  done: '✅',
  qr_scan: '📷',
  demo_matched: '💬',
  demo_done: '🎯',
  checkout_done: '👋',
  printer: '🖨️',
  attendees: '📋',
}

function FlowNode({ data, selected }) {
  const isIntegration = Boolean(data.kind)
  const icon = NODE_ICONS[data.screen] || NODE_ICONS[data.kind] || '▢'
  return (
    <div className={`flow-node${isIntegration ? ' integration' : ''}${selected ? ' selected' : ''}`}>
      <Handle type="target" position={Position.Left} />
      <div className="flow-node-inner">
        <span className="flow-node-icon">{icon}</span>
        <div>
          <div className="flow-node-title">{data.label || data.screen || data.kind}</div>
          <div className="flow-node-sub">
            {isIntegration ? 'Integrasjon · klikk for info' : 'Side · klikk for å redigere'}
          </div>
        </div>
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
    style: { stroke: 'rgba(234,85,153,0.55)' },
    labelStyle: { fill: 'rgba(255,255,255,0.65)', fontSize: 10 },
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
  const [overlayOpen, setOverlayOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [showHint, setShowHint] = useState(true)

  useEffect(() => {
    const flow = event.flow?.nodes ? event.flow : DEFAULT_FLOW
    setNodes(toRfNodes(flow))
    setEdges(toRfEdges(flow))
  }, [event.id, event.flow, setNodes, setEdges])

  const onNodeClick = useCallback((_evt, node) => {
    setSelected(node)
    setOverlayOpen(true)
    setShowHint(false)
  }, [])

  const onPaneClick = useCallback(() => {
    if (!overlayOpen) setSelected(null)
  }, [overlayOpen])

  async function save() {
    setSaving(true)
    setMessage('')
    try {
      await onSaveFlow(fromRf(nodes, edges))
      setMessage('Flyt lagret')
      setTimeout(() => setMessage(''), 2000)
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
      alert('Start-siden kan ikke slettes')
      return
    }
    if (!confirm(`Fjern «${selected.data?.label || selected.id}» fra flyten? Gjesten hopper over denne siden.`)) {
      return
    }
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
    setOverlayOpen(false)
  }

  function closeOverlay() {
    setOverlayOpen(false)
    setSelected(null)
  }

  return (
    <div className="canvas-wrap full">
      <div className="canvas-main">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode={null}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={18} color="#3a1a55" />
          <Controls />
          <MiniMap pannable zoomable />
          <Panel position="top-left" className="canvas-toolbar">
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Lagrer…' : 'Lagre flyt'}
            </button>
            <button className="btn btn-ghost" onClick={resetFlow}>
              Tilbakestill
            </button>
            {message && <span className="canvas-toast">{message}</span>}
          </Panel>
          <Panel position="top-right" className="canvas-legend">
            <span>▢ Side</span>
            <span>◈ Integrasjon</span>
            <span>→ Gjesteflyt</span>
          </Panel>
        </ReactFlow>

        {showHint && !overlayOpen && (
          <div className="canvas-hint">
            <h3>Slik fungerer canvas</h3>
            <ol>
              <li>
                <strong>Sidene</strong> er det gjesten ser på iPad-en (start → personvern → navn …).
              </li>
              <li>
                <strong>Pilene</strong> viser rekkefølgen. Fjern en side for å hoppe over den.
              </li>
              <li>
                <strong>Klikk på en side</strong> for forhåndsvisning og redigering.
              </li>
              <li>
                Oransje noder er <strong>integrasjoner</strong> (printer, deltakere) — ikke gjestesider.
              </li>
            </ol>
            <button type="button" className="btn btn-primary" onClick={() => setShowHint(false)}>
              Skjønner
            </button>
          </div>
        )}
      </div>

      {overlayOpen && selected && (
        <NodeEditOverlay
          selected={selected}
          event={event}
          onClose={closeOverlay}
          onRemove={removeSelected}
          onSaveSettings={onSaveSettings}
          onSaveFlow={save}
        />
      )}
    </div>
  )
}
