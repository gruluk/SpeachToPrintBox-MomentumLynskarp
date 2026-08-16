import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useEdgesState,
  useNodesState,
  MarkerType,
  Panel,
  ViewportPortal,
  getNodesBounds,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import NodeEditOverlay from './NodeEditOverlay'
import {
  CATALOG,
  ICONS,
  addItemToFlow,
  canAddItem,
  canRemoveNode,
  fullDefaultFlow,
  isMinimalFlow,
  migrateFlowEntries,
  nextSuggestion,
} from '../flowCatalog'

const nodeTypes = { screen: FlowNode, integration: FlowNode }

/** Extra room around nodes; grows as the flow grows. */
const EXTENT_PAD = 280
const EXTENT_MIN = 1000
const NODE_W = 180
const NODE_H = 72

function FlowNode({ data, selected }) {
  const isIntegration = Boolean(data.kind)
  const isEntry = data.kind === 'register_entry' || data.kind === 'checkout_entry'
  const icon = ICONS[data.screen] || ICONS[data.kind] || '▢'
  const sub = isEntry
    ? 'Inngang · styrer startknapp'
    : isIntegration
      ? 'Modul · klikk for info'
      : 'Side · klikk for å redigere'
  return (
    <div
      className={`flow-node${isIntegration ? ' integration' : ''}${isEntry ? ' entry' : ''}${selected ? ' selected' : ''}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="flow-node-inner">
        <span className="flow-node-icon">{icon}</span>
        <div>
          <div className="flow-node-title">{data.label || data.screen || data.kind}</div>
          <div className="flow-node-sub">{sub}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function nodesForBounds(nodes) {
  return (nodes || []).map((n) => ({
    ...n,
    width: n.measured?.width ?? n.width ?? NODE_W,
    height: n.measured?.height ?? n.height ?? NODE_H,
  }))
}

/** Bounded canvas area that expands with content. */
function computeExtent(nodes) {
  const sized = nodesForBounds(nodes)
  if (!sized.length) {
    return [
      [-EXTENT_PAD, -EXTENT_PAD],
      [EXTENT_MIN, EXTENT_MIN],
    ]
  }
  const b = getNodesBounds(sized)
  const maxX = Math.max(b.x + b.width + EXTENT_PAD, b.x + EXTENT_MIN * 0.5)
  const maxY = Math.max(b.y + b.height + EXTENT_PAD, b.y + EXTENT_MIN * 0.5)
  return [
    [b.x - EXTENT_PAD, b.y - EXTENT_PAD],
    [maxX, maxY],
  ]
}

function WorldBounds({ extent }) {
  const [[x0, y0], [x1, y1]] = extent
  return (
    <ViewportPortal>
      <div
        className="flow-world-bounds"
        style={{
          transform: `translate(${x0}px, ${y0}px)`,
          width: Math.max(0, x1 - x0),
          height: Math.max(0, y1 - y0),
        }}
      />
    </ViewportPortal>
  )
}

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
    labelStyle: {
      fill: '#f5e9ff',
      fontSize: 10,
      fontWeight: 600,
    },
    labelBgStyle: {
      fill: '#2a1048',
      fillOpacity: 0.95,
      stroke: 'rgba(234,85,153,0.35)',
      strokeWidth: 1,
    },
    labelBgPadding: [4, 6],
    labelBgBorderRadius: 4,
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
  const location = useLocation()
  const navigate = useNavigate()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selected, setSelected] = useState(null)
  const [overlayOpen, setOverlayOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [guideDismissed, setGuideDismissed] = useState(false)
  const [skippedKeys, setSkippedKeys] = useState([])

  const startGuided =
    Boolean(location.state?.guide) || isMinimalFlow(event.flow?.nodes ? event.flow.nodes : [])

  useEffect(() => {
    const raw = event.flow?.nodes ? event.flow : fullDefaultFlow()
    const flow = migrateFlowEntries(raw)
    setNodes(toRfNodes(flow))
    setEdges(toRfEdges(flow))
  }, [event.id, event.flow, setNodes, setEdges])

  const suggestion = useMemo(() => nextSuggestion(nodes, skippedKeys), [nodes, skippedKeys])
  const showGuide = !guideDismissed && !overlayOpen && !addOpen && Boolean(suggestion || startGuided)
  const extent = useMemo(() => computeExtent(nodes), [nodes])

  const onNodeClick = useCallback((_evt, node) => {
    setSelected(node)
    setOverlayOpen(true)
    setAddOpen(false)
  }, [])

  const onPaneClick = useCallback(() => {
    if (!overlayOpen) setSelected(null)
    setAddOpen(false)
  }, [overlayOpen])

  async function save(nextNodes = nodes, nextEdges = edges) {
    setSaving(true)
    setMessage('')
    try {
      await onSaveFlow(fromRf(nextNodes, nextEdges))
      setMessage('Flyt lagret')
      setTimeout(() => setMessage(''), 2000)
    } catch (e) {
      setMessage(e.message)
    } finally {
      setSaving(false)
    }
  }

  function applyFlow(result, { autoSave = true } = {}) {
    if (result.error) {
      setMessage(result.error)
      setTimeout(() => setMessage(''), 3500)
      return
    }
    const rfNodes = toRfNodes(result)
    const rfEdges = toRfEdges(result)
    setNodes(rfNodes)
    setEdges(rfEdges)
    if (autoSave) save(rfNodes, rfEdges)
  }

  function addCatalogItem(key) {
    const result = addItemToFlow(fromRf(nodes, edges).nodes, fromRf(nodes, edges).edges, key)
    if (result.error) {
      setMessage(result.error)
      setTimeout(() => setMessage(''), 3500)
      return
    }
    applyFlow(result)
    setAddOpen(false)
  }

  function acceptSuggestion() {
    if (!suggestion?.key) return
    addCatalogItem(suggestion.key)
  }

  function skipSuggestion() {
    if (!suggestion?.key) {
      setGuideDismissed(true)
      return
    }
    setSkippedKeys((keys) => [...keys, suggestion.key])
  }

  function resetFlow() {
    if (!confirm('Tilbakestill til full standardflyt?')) return
    const flow = fullDefaultFlow()
    setNodes(toRfNodes(flow))
    setEdges(toRfEdges(flow))
  }

  function clearToStart() {
    if (!confirm('Tøm flyten til kun Start-siden?')) return
    applyFlow({
      nodes: [
        {
          id: 'start',
          type: 'screen',
          position: { x: 80, y: 200 },
          data: { screen: 'start', label: 'Start' },
        },
      ],
      edges: [],
    })
    setGuideDismissed(false)
  }

  function removeSelected() {
    if (!selected) return
    const check = canRemoveNode(selected, nodes)
    if (!check.ok) {
      alert(check.reason)
      return
    }
    if (!confirm(`Fjern «${selected.data?.label || selected.id}» fra flyten?`)) return
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
    setOverlayOpen(false)
  }

  function closeOverlay() {
    setOverlayOpen(false)
    setSelected(null)
  }

  function dismissGuideNav() {
    if (location.state?.guide) {
      navigate(location.pathname, { replace: true, state: {} })
    }
    setGuideDismissed(true)
  }

  const addable = CATALOG.filter((c) => !c.locked)

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
          fitViewOptions={{ padding: 0.2 }}
          deleteKeyCode={null}
          proOptions={{ hideAttribution: true }}
          translateExtent={extent}
          nodeExtent={extent}
          minZoom={0.35}
          maxZoom={1.75}
        >
          <Background gap={18} color="#3a1a55" />
          <WorldBounds extent={extent} />
          <Controls showInteractive={false} />
          <Panel position="top-left" className="canvas-toolbar">
            <button className="btn btn-primary" onClick={() => save()} disabled={saving}>
              {saving ? 'Lagrer…' : 'Lagre flyt'}
            </button>
            <button className="btn btn-ghost" onClick={resetFlow} type="button">
              Full mal
            </button>
            <button className="btn btn-ghost" onClick={clearToStart} type="button">
              Kun Start
            </button>
            {message && <span className="canvas-toast">{message}</span>}
          </Panel>
          <Panel position="top-right" className="canvas-legend">
            <span>▢ Side</span>
            <span>◈ Modul</span>
            <span>→ Gjesteflyt</span>
          </Panel>
        </ReactFlow>

        <button
          type="button"
          className={`canvas-add-fab${addOpen ? ' open' : ''}`}
          onClick={() => {
            setAddOpen((o) => !o)
            setOverlayOpen(false)
          }}
          title="Legg til side eller modul"
          aria-label="Legg til side eller modul"
        >
          {addOpen ? '×' : '+'}
        </button>

        {addOpen && (
          <div className="canvas-add-menu">
            <header className="canvas-add-header">
              <h3>Legg til</h3>
              <p className="muted">Sider og moduler. Grå = mangler avhengighet.</p>
            </header>
            <div className="canvas-add-section">
              <p className="canvas-add-label">Moduler</p>
              {addable
                .filter((c) => c.category === 'module')
                .map((item) => (
                  <AddMenuItem key={item.key} item={item} nodes={nodes} onAdd={addCatalogItem} />
                ))}
            </div>
            <div className="canvas-add-section">
              <p className="canvas-add-label">Sider</p>
              {addable
                .filter((c) => c.category === 'page')
                .map((item) => (
                  <AddMenuItem key={item.key} item={item} nodes={nodes} onAdd={addCatalogItem} />
                ))}
            </div>
          </div>
        )}

        {showGuide && suggestion && (
          <div className="canvas-guide">
            <p className="canvas-guide-kicker">Foreslått neste steg</p>
            <h3>{suggestion.title}</h3>
            <p className="muted">{suggestion.body}</p>
            <div className="canvas-guide-actions">
              <button type="button" className="btn btn-primary" onClick={acceptSuggestion}>
                Ja, legg til
              </button>
              <button type="button" className="btn btn-ghost" onClick={skipSuggestion}>
                Ikke nå
              </button>
              <button type="button" className="btn btn-ghost" onClick={dismissGuideNav}>
                Skjul forslag
              </button>
            </div>
          </div>
        )}

        {showGuide && !suggestion && (
          <div className="canvas-guide">
            <p className="canvas-guide-kicker">Flyten er komplett</p>
            <h3>Alle foreslåtte steg er på plass</h3>
            <p className="muted">
              Bruk + for å justere, eller klikk en node for å redigere. Du kan fortsatt fjerne eller legge til
              mer.
            </p>
            <div className="canvas-guide-actions">
              <button type="button" className="btn btn-primary" onClick={dismissGuideNav}>
                Skjønner
              </button>
            </div>
          </div>
        )}

        {!showGuide && !overlayOpen && !addOpen && suggestion && (
          <button
            type="button"
            className="canvas-guide-pill"
            onClick={() => setGuideDismissed(false)}
          >
            Vis neste steg-forslag
          </button>
        )}
      </div>

      {overlayOpen && selected && (
        <NodeEditOverlay
          selected={selected}
          event={event}
          flow={fromRf(nodes, edges)}
          onClose={closeOverlay}
          onRemove={removeSelected}
          onSaveSettings={onSaveSettings}
          onSaveFlow={() => save()}
        />
      )}
    </div>
  )
}

function AddMenuItem({ item, nodes, onAdd }) {
  const check = canAddItem(item, nodes)
  const icon = ICONS[item.key] || '▢'
  return (
    <button
      type="button"
      className={`canvas-add-item${check.ok ? '' : ' locked'}`}
      disabled={!check.ok}
      onClick={() => onAdd(item.key)}
      title={check.ok ? item.description : check.reason}
    >
      <span className="canvas-add-item-icon">{icon}</span>
      <span className="canvas-add-item-text">
        <strong>{item.label}</strong>
        <span className="muted">{check.ok ? item.description : check.reason}</span>
      </span>
    </button>
  )
}
