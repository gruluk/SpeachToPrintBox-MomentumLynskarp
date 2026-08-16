import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Handle,
  Position,
  useEdgesState,
  useNodesState,
  useReactFlow,
  addEdge,
  MarkerType,
  Panel,
  ViewportPortal,
  getNodesBounds,
  ConnectionMode,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import NodeEditOverlay from './NodeEditOverlay'
import {
  CATALOG,
  FLOW_ACTIONS,
  ICONS,
  addItemToFlow,
  canAddItem,
  canRemoveNode,
  fullDefaultFlow,
  inferEdgeAction,
  isMinimalFlow,
  migrateFlowEntries,
  nextSuggestion,
  nodeKey,
  suggestedActionsForNode,
} from '../flowCatalog'

const nodeTypes = { screen: FlowNode, integration: FlowNode }

const EXTENT_PAD = 280
const EXTENT_MIN = 1000
const NODE_W = 180
const NODE_H = 72

const EDGE_STYLE = {
  stroke: 'rgba(234,85,153,0.55)',
}

const EDGE_LABEL_STYLE = {
  fill: '#f5e9ff',
  fontSize: 10,
  fontWeight: 600,
}

const EDGE_LABEL_BG = {
  fill: '#2a1048',
  fillOpacity: 0.95,
  stroke: 'rgba(234,85,153,0.35)',
  strokeWidth: 1,
}

function decorateEdge(e) {
  const action = e.data?.action || e.label || 'next'
  return {
    ...e,
    label: action,
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { ...(e.data || {}), action },
    style: EDGE_STYLE,
    labelStyle: EDGE_LABEL_STYLE,
    labelBgStyle: EDGE_LABEL_BG,
    labelBgPadding: [4, 6],
    labelBgBorderRadius: 4,
    animated: false,
    updatable: true,
  }
}

function FlowNode({ data, selected }) {
  const isIntegration = Boolean(data.kind)
  const isEntry = data.kind === 'register_entry' || data.kind === 'checkout_entry'
  const icon = ICONS[data.screen] || ICONS[data.kind] || '▢'
  const sub = isEntry
    ? 'Inngang · trekk pil videre'
    : isIntegration
      ? 'Modul · trekk pil for å koble'
      : 'Side · trekk fra ● for å koble'
  return (
    <div
      className={`flow-node${isIntegration ? ' integration' : ''}${isEntry ? ' entry' : ''}${selected ? ' selected' : ''}`}
    >
      <Handle type="target" position={Position.Left} className="flow-handle" />
      <div className="flow-node-inner">
        <span className="flow-node-icon">{icon}</span>
        <div>
          <div className="flow-node-title">{data.label || data.screen || data.kind}</div>
          <div className="flow-node-sub">{sub}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="flow-handle" />
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
  return (flow?.edges || []).map((e) =>
    decorateEdge({
      id: e.id,
      source: e.source,
      target: e.target,
      data: e.data || {},
    }),
  )
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

export default function FlowCanvas(props) {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner {...props} />
    </ReactFlowProvider>
  )
}

function FlowCanvasInner({ event, onSaveFlow, onSaveSettings }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { screenToFlowPosition, getNodes } = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selected, setSelected] = useState(null)
  const [selectedEdge, setSelectedEdge] = useState(null)
  const [overlayOpen, setOverlayOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [guideDismissed, setGuideDismissed] = useState(false)
  const [skippedKeys, setSkippedKeys] = useState([])
  const [connectHint, setConnectHint] = useState(true)

  const startGuided =
    Boolean(location.state?.guide) || isMinimalFlow(event.flow?.nodes ? event.flow.nodes : [])

  useEffect(() => {
    const raw = event.flow?.nodes ? event.flow : fullDefaultFlow()
    const flow = migrateFlowEntries(raw)
    setNodes(toRfNodes(flow))
    setEdges(toRfEdges(flow))
  }, [event.id, event.flow, setNodes, setEdges])

  const suggestion = useMemo(() => nextSuggestion(nodes, skippedKeys), [nodes, skippedKeys])
  const showGuide =
    !guideDismissed && !overlayOpen && !addOpen && !selectedEdge && Boolean(suggestion || startGuided)
  const extent = useMemo(() => computeExtent(nodes), [nodes])

  const onNodeClick = useCallback((_evt, node) => {
    setSelected(node)
    setSelectedEdge(null)
    setOverlayOpen(true)
    setAddOpen(false)
  }, [])

  const onEdgeClick = useCallback((_evt, edge) => {
    setSelectedEdge(edge)
    setOverlayOpen(false)
    setSelected(null)
    setAddOpen(false)
    setConnectHint(false)
  }, [])

  const onPaneClick = useCallback(() => {
    if (!overlayOpen) setSelected(null)
    setSelectedEdge(null)
    setAddOpen(false)
  }, [overlayOpen])

  const onConnect = useCallback(
    (connection) => {
      const source = getNodes().find((n) => n.id === connection.source)
      const target = getNodes().find((n) => n.id === connection.target)
      const action = inferEdgeAction(source, target)
      setEdges((eds) =>
        addEdge(
          decorateEdge({
            ...connection,
            id: `e_${connection.source}_${connection.target}_${action}_${Math.random().toString(36).slice(2, 6)}`,
            data: { action },
          }),
          eds,
        ),
      )
      setConnectHint(false)
      setMessage(`Koblet med handling «${action}» — klikk pilen for å endre`)
      setTimeout(() => setMessage(''), 3500)
    },
    [getNodes, setEdges],
  )

  const onReconnect = useCallback(
    (oldEdge, newConnection) => {
      setEdges((eds) => {
        const next = eds.filter((e) => e.id !== oldEdge.id)
        const source = getNodes().find((n) => n.id === newConnection.source)
        const target = getNodes().find((n) => n.id === newConnection.target)
        const action = oldEdge.data?.action || inferEdgeAction(source, target)
        return addEdge(
          decorateEdge({
            ...newConnection,
            id: oldEdge.id,
            data: { action },
          }),
          next,
        )
      })
    },
    [getNodes, setEdges],
  )

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
    if (result.warning) {
      setMessage(result.warning)
      setTimeout(() => setMessage(''), 4000)
    }
    if (autoSave) save(rfNodes, rfEdges)
  }

  function placementForNew() {
    try {
      const center = screenToFlowPosition({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2,
      })
      return { x: center.x - 90, y: center.y - 36 }
    } catch {
      return undefined
    }
  }

  function addCatalogItem(key) {
    const result = addItemToFlow(fromRf(nodes, edges).nodes, fromRf(nodes, edges).edges, key, {
      wire: false,
      position: placementForNew(),
    })
    if (result.error) {
      setMessage(result.error)
      setTimeout(() => setMessage(''), 3500)
      return
    }
    applyFlow(result)
    setAddOpen(false)
    setConnectHint(true)
    setMessage('Lagt til — trekk en pil fra en node til den nye for å koble')
    setTimeout(() => setMessage(''), 4000)
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
    if (!confirm('Tilbakestill til full standardflyt (med ferdige koblinger)?')) return
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
    const warn = check.warning ? `\n\n${check.warning}` : ''
    if (!confirm(`Fjern «${selected.data?.label || selected.id}» fra flyten?${warn}`)) return
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
    setOverlayOpen(false)
  }

  function updateEdgeAction(edgeId, action) {
    setEdges((eds) =>
      eds.map((e) =>
        e.id === edgeId
          ? decorateEdge({
              ...e,
              data: { ...(e.data || {}), action },
            })
          : e,
      ),
    )
    setSelectedEdge((e) =>
      e && e.id === edgeId
        ? decorateEdge({ ...e, data: { ...(e.data || {}), action } })
        : e,
    )
  }

  function deleteSelectedEdge() {
    if (!selectedEdge) return
    setEdges((eds) => eds.filter((e) => e.id !== selectedEdge.id))
    setSelectedEdge(null)
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
  const sourceNode = selectedEdge ? nodes.find((n) => n.id === selectedEdge.source) : null

  return (
    <div className="canvas-wrap full">
      <div className="canvas-main">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onReconnect={onReconnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          deleteKeyCode={null}
          edgesReconnectable
          elementsSelectable
          connectionMode={ConnectionMode.Loose}
          connectionLineStyle={{ stroke: '#ea5599', strokeWidth: 2 }}
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
            <span>→ Trekk pil for å koble</span>
          </Panel>
        </ReactFlow>

        {connectHint && !overlayOpen && !selectedEdge && nodes.length > 1 && (
          <div className="canvas-connect-hint">
            <strong>Koble selv:</strong> dra fra den høyre ● på en node til en annen. Klikk deretter
            på pilen for å velge hvilken knapp/handling den er.
            <button type="button" className="btn btn-ghost" onClick={() => setConnectHint(false)}>
              Skjul
            </button>
          </div>
        )}

        <button
          type="button"
          className={`canvas-add-fab${addOpen ? ' open' : ''}`}
          onClick={() => {
            setAddOpen((o) => !o)
            setOverlayOpen(false)
            setSelectedEdge(null)
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
              <p className="muted">
                Byggeklosser legges løst på canvas. Du kobler dem selv med piler.
              </p>
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

        {selectedEdge && (
          <EdgeEditPanel
            edge={selectedEdge}
            sourceNode={sourceNode}
            nodes={nodes}
            onChangeAction={updateEdgeAction}
            onDelete={deleteSelectedEdge}
            onClose={() => setSelectedEdge(null)}
            onRetarget={(targetId) => {
              setEdges((eds) =>
                eds.map((e) =>
                  e.id === selectedEdge.id
                    ? decorateEdge({ ...e, target: targetId })
                    : e,
                ),
              )
              setSelectedEdge((e) => (e ? decorateEdge({ ...e, target: targetId }) : e))
            }}
          />
        )}

        {showGuide && suggestion && (
          <div className="canvas-guide">
            <p className="canvas-guide-kicker">Foreslått byggekloss</p>
            <h3>{suggestion.title}</h3>
            <p className="muted">
              {suggestion.body} Etterpå: trekk en pil for å bestemme når den skal vises.
            </p>
            <div className="canvas-guide-actions">
              <button type="button" className="btn btn-primary" onClick={acceptSuggestion}>
                Legg til (uten kobling)
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
            <p className="canvas-guide-kicker">Klar</p>
            <h3>Bygg videre med + og piler</h3>
            <p className="muted">
              Legg til sider/moduler, trekk koblinger, og klikk på pilene for å styre knapper
              (Neste, Registrer, Vil ha demo, …).
            </p>
            <div className="canvas-guide-actions">
              <button type="button" className="btn btn-primary" onClick={dismissGuideNav}>
                Skjønner
              </button>
            </div>
          </div>
        )}

        {!showGuide && !overlayOpen && !addOpen && !selectedEdge && suggestion && (
          <button
            type="button"
            className="canvas-guide-pill"
            onClick={() => setGuideDismissed(false)}
          >
            Vis neste forslag
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

function EdgeEditPanel({ edge, sourceNode, nodes, onChangeAction, onDelete, onClose, onRetarget }) {
  const action = edge.data?.action || edge.label || 'next'
  const suggested = suggestedActionsForNode(sourceNode)
  const targetOptions = nodes.filter((n) => n.id !== edge.source)
  const target = nodes.find((n) => n.id === edge.target)

  return (
    <div className="edge-edit-panel">
      <header className="edge-edit-header">
        <div>
          <p className="canvas-guide-kicker">Kobling</p>
          <h3>
            {sourceNode?.data?.label || edge.source} → {target?.data?.label || edge.target}
          </h3>
        </div>
        <button type="button" className="btn btn-ghost" onClick={onClose}>
          Lukk
        </button>
      </header>

      <label className="field">
        Handling (hvilken knapp / overgang)
        <select
          className="select"
          value={action}
          onChange={(e) => onChangeAction(edge.id, e.target.value)}
        >
          {FLOW_ACTIONS.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
              {suggested.includes(a.value) ? ' ★' : ''}
            </option>
          ))}
        </select>
      </label>
      <p className="muted" style={{ fontSize: '0.8rem', marginTop: '-0.35rem' }}>
        ★ = vanlig for denne siden. Booth følger denne handlingen når gjesten trykker knappen.
      </p>

      <label className="field">
        Går til
        <select
          className="select"
          value={edge.target}
          onChange={(e) => onRetarget(e.target.value)}
        >
          {targetOptions.map((n) => (
            <option key={n.id} value={n.id}>
              {n.data?.label || n.id}
            </option>
          ))}
        </select>
      </label>

      <div className="row" style={{ marginTop: '0.75rem' }}>
        <button type="button" className="btn btn-ghost danger" onClick={onDelete}>
          Slett kobling
        </button>
      </div>
    </div>
  )
}

function AddMenuItem({ item, nodes, onAdd }) {
  const check = canAddItem(item, nodes, { enforceDeps: false })
  const icon = ICONS[item.key] || '▢'
  const blocked = !check.ok
  return (
    <button
      type="button"
      className={`canvas-add-item${blocked ? ' locked' : ''}${check.warning ? ' warn' : ''}`}
      disabled={blocked}
      onClick={() => onAdd(item.key)}
      title={blocked ? check.reason : check.warning || item.description}
    >
      <span className="canvas-add-item-icon">{icon}</span>
      <span className="canvas-add-item-text">
        <strong>{item.label}</strong>
        <span className="muted">{blocked ? check.reason : check.warning || item.description}</span>
      </span>
    </button>
  )
}
