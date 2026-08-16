/** Pages, modules, dependencies, and helpers for building booth flows. */

export const LABELS = {
  start: 'Start',
  privacy: 'Personvern',
  name_input: 'Navneoppslag',
  interest_select: 'Interesser',
  done: 'Ferdig',
  qr_scan: 'QR-skanning',
  demo_matched: 'Demo',
  demo_done: 'Demo ferdig',
  checkout_done: 'Utsjekk',
  printer: 'Printer',
  attendees: 'Deltakere',
}

export const ICONS = {
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

/**
 * Catalog of addable items.
 * `dependsOn`: keys (screen or kind) that must already exist in the flow.
 * `unique`: only one of this item allowed.
 */
export const CATALOG = [
  {
    key: 'start',
    type: 'screen',
    screen: 'start',
    category: 'page',
    label: 'Start / Velkommen',
    description: 'Første side gjesten ser. Kan ikke fjernes.',
    unique: true,
    locked: true,
    dependsOn: [],
  },
  {
    key: 'attendees',
    type: 'integration',
    kind: 'attendees',
    category: 'module',
    label: 'Deltakere',
    description: 'Deltakerliste for navne- og QR-oppslag. Importer under fanen Deltakere.',
    unique: true,
    dependsOn: [],
  },
  {
    key: 'printer',
    type: 'integration',
    kind: 'printer',
    category: 'module',
    label: 'Printer',
    description: 'Køer navneskilt til etikettprinteren.',
    unique: true,
    dependsOn: ['interest_select'],
  },
  {
    key: 'privacy',
    type: 'screen',
    screen: 'privacy',
    category: 'page',
    label: 'Personvern',
    description: 'Samtykkeside før registrering.',
    unique: true,
    dependsOn: [],
  },
  {
    key: 'name_input',
    type: 'screen',
    screen: 'name_input',
    category: 'page',
    label: 'Navneoppslag',
    description: 'Gjesten finner seg selv i listen.',
    unique: true,
    dependsOn: ['attendees'],
  },
  {
    key: 'interest_select',
    type: 'screen',
    screen: 'interest_select',
    category: 'page',
    label: 'Interesser',
    description: 'Velg temaer som trykkes på navneskiltet.',
    unique: true,
    dependsOn: ['name_input'],
  },
  {
    key: 'done',
    type: 'screen',
    screen: 'done',
    category: 'page',
    label: 'Ferdig',
    description: 'Bekreftelse etter registrering.',
    unique: true,
    dependsOn: ['name_input'],
  },
  {
    key: 'qr_scan',
    type: 'screen',
    screen: 'qr_scan',
    category: 'page',
    label: 'QR-skanning',
    description: 'Utsjekk: skann QR på navneskiltet.',
    unique: true,
    dependsOn: ['attendees'],
  },
  {
    key: 'demo_matched',
    type: 'screen',
    screen: 'demo_matched',
    category: 'page',
    label: 'Demo-spørsmål',
    description: 'Spør om demo etter QR-skanning.',
    unique: true,
    dependsOn: ['qr_scan'],
  },
  {
    key: 'demo_done',
    type: 'screen',
    screen: 'demo_done',
    category: 'page',
    label: 'Demo ferdig',
    description: 'Bekreftelse hvis de vil ha demo.',
    unique: true,
    dependsOn: ['demo_matched'],
  },
  {
    key: 'checkout_done',
    type: 'screen',
    screen: 'checkout_done',
    category: 'page',
    label: 'Utsjekk ferdig',
    description: 'Bekreftelse hvis de ikke vil ha demo.',
    unique: true,
    dependsOn: ['demo_matched'],
  },
]

/** Guided order: suggest the next missing step once dependencies are met. */
const SUGGESTIONS = [
  {
    key: 'attendees',
    title: 'Legg til Deltakere-modul?',
    body: 'Navneoppslag og QR-utsjekk trenger en deltakerliste. Uten denne modulen kan du ikke legge til de sidene.',
  },
  {
    key: 'privacy',
    title: 'Personvern-samtykke?',
    body: 'Anbefalt når dere lagrer personopplysninger. Gjesten må krysse av før registrering.',
  },
  {
    key: 'name_input',
    title: 'Navneoppslag?',
    body: 'Gjesten søker opp seg selv i deltakerlisten (eller registrerer walk-up hvis det er på).',
  },
  {
    key: 'interest_select',
    title: 'Interesseområder?',
    body: 'La gjesten velge temaer som trykkes på navneskiltet.',
  },
  {
    key: 'printer',
    title: 'Koble til printer?',
    body: 'Når interesser er valgt, køes en etikett til Brother-printeren.',
  },
  {
    key: 'done',
    title: 'Ferdig-side?',
    body: 'Vis en bekreftelse etter at registreringen er fullført.',
  },
  {
    key: 'qr_scan',
    title: 'Utsjekk med QR?',
    body: 'Andre knapp på startsiden: skann QR på navneskiltet for demo/utsjekk.',
  },
  {
    key: 'demo_matched',
    title: 'Demo-spørsmål?',
    body: 'Etter QR-skanning: spør om gjesten vil ha en demo.',
  },
  {
    key: 'demo_done',
    title: 'Bekreftelse for demo?',
    body: 'Side som vises når gjesten sier ja til demo.',
  },
  {
    key: 'checkout_done',
    title: 'Bekreftelse uten demo?',
    body: 'Side som vises når gjesten sier nei takk.',
  },
]

export function catalogByKey(key) {
  return CATALOG.find((c) => c.key === key) || null
}

export function nodeKey(node) {
  return node?.data?.screen || node?.data?.kind || null
}

export function presentKeys(nodes) {
  const set = new Set()
  for (const n of nodes || []) {
    const k = nodeKey(n)
    if (k) set.add(k)
  }
  return set
}

export function findNodeByKey(nodes, key) {
  return (nodes || []).find((n) => nodeKey(n) === key) || null
}

export function canAddItem(item, nodes) {
  if (!item) return { ok: false, reason: 'Ukjent element' }
  if (item.locked) return { ok: false, reason: 'Allerede i flyten' }
  const present = presentKeys(nodes)
  if (item.unique && present.has(item.key)) {
    return { ok: false, reason: 'Allerede lagt til' }
  }
  const missing = (item.dependsOn || []).filter((d) => !present.has(d))
  if (missing.length) {
    const labels = missing.map((k) => LABELS[k] || k).join(', ')
    return {
      ok: false,
      reason: `Krever først: ${labels}`,
      missing,
    }
  }
  return { ok: true }
}

export function canRemoveNode(node, nodes) {
  const key = nodeKey(node)
  if (key === 'start') return { ok: false, reason: 'Start-siden kan ikke slettes' }
  const dependents = CATALOG.filter(
    (c) => (c.dependsOn || []).includes(key) && findNodeByKey(nodes, c.key),
  )
  if (dependents.length) {
    const labels = dependents.map((d) => d.label).join(', ')
    return {
      ok: false,
      reason: `Fjern først: ${labels}`,
      dependents,
    }
  }
  return { ok: true }
}

export function nextSuggestion(nodes, excludeKeys = []) {
  const present = presentKeys(nodes)
  const skip = new Set(excludeKeys)
  for (const s of SUGGESTIONS) {
    if (present.has(s.key) || skip.has(s.key)) continue
    const item = catalogByKey(s.key)
    const check = canAddItem(item, nodes)
    if (!check.ok) continue
    return { ...s, item }
  }
  return null
}

export function emptyStartFlow() {
  return {
    nodes: [
      {
        id: 'start',
        type: 'screen',
        position: { x: 80, y: 200 },
        data: { screen: 'start', label: LABELS.start },
      },
    ],
    edges: [],
  }
}

export function fullDefaultFlow() {
  return {
    nodes: [
      { id: 'start', type: 'screen', position: { x: 80, y: 200 }, data: { screen: 'start', label: LABELS.start } },
      { id: 'privacy', type: 'screen', position: { x: 320, y: 80 }, data: { screen: 'privacy', label: LABELS.privacy } },
      { id: 'name', type: 'screen', position: { x: 560, y: 80 }, data: { screen: 'name_input', label: LABELS.name_input } },
      { id: 'interests', type: 'screen', position: { x: 800, y: 80 }, data: { screen: 'interest_select', label: LABELS.interest_select } },
      { id: 'done', type: 'screen', position: { x: 1040, y: 80 }, data: { screen: 'done', label: LABELS.done } },
      { id: 'qr', type: 'screen', position: { x: 320, y: 320 }, data: { screen: 'qr_scan', label: LABELS.qr_scan } },
      { id: 'demo_matched', type: 'screen', position: { x: 560, y: 320 }, data: { screen: 'demo_matched', label: LABELS.demo_matched } },
      { id: 'demo_done', type: 'screen', position: { x: 800, y: 280 }, data: { screen: 'demo_done', label: LABELS.demo_done } },
      { id: 'checkout_done', type: 'screen', position: { x: 800, y: 400 }, data: { screen: 'checkout_done', label: LABELS.checkout_done } },
      { id: 'printer', type: 'integration', position: { x: 1040, y: 280 }, data: { kind: 'printer', label: LABELS.printer } },
      { id: 'db', type: 'integration', position: { x: 80, y: 400 }, data: { kind: 'attendees', label: LABELS.attendees } },
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
}

export function isMinimalFlow(nodes) {
  return (nodes || []).length <= 1 && presentKeys(nodes).has('start')
}

function uid(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`
}

function nextEdgeId(edges) {
  return uid('e')
}

function defaultPosition(key, nodes) {
  const byKey = {
    attendees: { x: 80, y: 400 },
    privacy: { x: 320, y: 80 },
    name_input: { x: 560, y: 80 },
    interest_select: { x: 800, y: 80 },
    done: { x: 1040, y: 80 },
    printer: { x: 1040, y: 280 },
    qr_scan: { x: 320, y: 340 },
    demo_matched: { x: 560, y: 340 },
    demo_done: { x: 800, y: 300 },
    checkout_done: { x: 800, y: 420 },
  }
  if (byKey[key]) return byKey[key]
  const maxX = Math.max(80, ...(nodes || []).map((n) => n.position?.x || 0))
  return { x: maxX + 240, y: 200 }
}

function nodeIdFor(item) {
  const map = {
    attendees: 'db',
    name_input: 'name',
    interest_select: 'interests',
    qr_scan: 'qr',
  }
  return map[item.key] || item.key
}

/**
 * Add a catalog item to the flow and wire sensible default edges.
 * @returns {{ nodes, edges } | { error: string }}
 */
export function addItemToFlow(nodes, edges, key) {
  const item = catalogByKey(key)
  const check = canAddItem(item, nodes)
  if (!check.ok) return { error: check.reason }

  let nextNodes = [...(nodes || [])]
  let nextEdges = [...(edges || [])]

  const id = nodeIdFor(item)
  if (nextNodes.some((n) => n.id === id)) {
    return { error: 'Allerede lagt til' }
  }

  const data =
    item.type === 'integration'
      ? { kind: item.kind, label: item.label }
      : { screen: item.screen, label: item.label }

  nextNodes.push({
    id,
    type: item.type === 'integration' ? 'integration' : 'screen',
    position: defaultPosition(item.key, nextNodes),
    data,
  })

  const byKey = (k) => findNodeByKey(nextNodes, k)
  const pushEdge = (source, target, action) => {
    if (!source || !target) return
    const exists = nextEdges.some(
      (e) => e.source === source.id && e.target === target.id && (e.data?.action || e.label) === action,
    )
    if (exists) return
    nextEdges.push({
      id: nextEdgeId(nextEdges),
      source: source.id,
      target: target.id,
      data: { action },
    })
  }

  const start = byKey('start')
  const privacy = byKey('privacy')
  const name = byKey('name_input')
  const interests = byKey('interest_select')
  const done = byKey('done')
  const attendees = byKey('attendees')
  const printer = byKey('printer')
  const qr = byKey('qr_scan')
  const demo = byKey('demo_matched')
  const demoDone = byKey('demo_done')
  const checkoutDone = byKey('checkout_done')

  if (item.key === 'privacy') {
    // start → privacy (register); if name exists, privacy → name and drop start→name register
    pushEdge(start, privacy, 'register')
    if (name) {
      nextEdges = nextEdges.filter(
        (e) => !(e.source === start?.id && e.target === name.id && (e.data?.action || e.label) === 'register'),
      )
      pushEdge(privacy, name, 'next')
    }
  }

  if (item.key === 'name_input') {
    if (privacy) {
      pushEdge(privacy, name, 'next')
    } else {
      pushEdge(start, name, 'register')
    }
    pushEdge(name, attendees, 'lookup')
  }

  if (item.key === 'interest_select') {
    pushEdge(name, interests, 'next')
    // If done was wired from name, rewire through interests
    if (done) {
      nextEdges = nextEdges.filter(
        (e) => !(e.source === name?.id && e.target === done.id && (e.data?.action || e.label) === 'next'),
      )
      pushEdge(interests, done, 'next')
    }
  }

  if (item.key === 'done') {
    if (interests) pushEdge(interests, done, 'next')
    else pushEdge(name, done, 'next')
  }

  if (item.key === 'printer') {
    pushEdge(interests, printer, 'print_label')
  }

  if (item.key === 'qr_scan') {
    pushEdge(start, qr, 'checkout')
  }

  if (item.key === 'demo_matched') {
    pushEdge(qr, demo, 'next')
  }

  if (item.key === 'demo_done') {
    pushEdge(demo, demoDone, 'wants_demo')
  }

  if (item.key === 'checkout_done') {
    pushEdge(demo, checkoutDone, 'no_demo')
  }

  return { nodes: nextNodes, edges: nextEdges }
}
