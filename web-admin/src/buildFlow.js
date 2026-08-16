/** Build InstantDB flow graph from wizard answers. */

const LABELS = {
  start: 'Start',
  privacy: 'Personvern',
  name_input: 'Navn',
  interest_select: 'Interesser',
  done: 'Ferdig',
  qr_scan: 'QR-skanning',
  demo_matched: 'Demo',
  demo_done: 'Demo ferdig',
  checkout_done: 'Utsjekk',
  printer: 'Printer',
  attendees: 'Deltakere',
}

function node(id, type, x, y, data) {
  return {
    id,
    type,
    position: { x, y },
    data: {
      label: data.label || LABELS[data.screen] || LABELS[data.kind] || id,
      ...data,
    },
  }
}

function edge(id, source, target, action) {
  return { id, source, target, data: { action } }
}

/**
 * @param {{
 *   includeRegister: boolean,
 *   includeCheckout: boolean,
 *   includePrivacy: boolean,
 *   includeInterests: boolean,
 *   includePrinter: boolean,
 * }} answers
 */
export function buildFlowFromAnswers(answers) {
  const {
    includeRegister = true,
    includeCheckout = true,
    includePrivacy = true,
    includeInterests = true,
    includePrinter = true,
  } = answers

  const nodes = []
  const edges = []
  let eid = 1

  nodes.push(node('start', 'screen', 80, 200, { screen: 'start' }))
  nodes.push(node('db', 'integration', 80, 420, { kind: 'attendees' }))

  if (includeRegister) {
    let prev = 'start'
    let x = 300

    if (includePrivacy) {
      nodes.push(node('privacy', 'screen', x, 80, { screen: 'privacy' }))
      edges.push(edge(`e${eid++}`, prev, 'privacy', 'register'))
      prev = 'privacy'
      x += 240
    } else {
      // register goes straight to name
    }

    nodes.push(node('name', 'screen', x, 80, { screen: 'name_input' }))
    if (includePrivacy) {
      edges.push(edge(`e${eid++}`, prev, 'name', 'next'))
    } else {
      edges.push(edge(`e${eid++}`, 'start', 'name', 'register'))
    }
    edges.push(edge(`e${eid++}`, 'name', 'db', 'lookup'))
    prev = 'name'
    x += 240

    if (includeInterests) {
      nodes.push(node('interests', 'screen', x, 80, { screen: 'interest_select' }))
      edges.push(edge(`e${eid++}`, prev, 'interests', 'next'))
      prev = 'interests'
      x += 240
    }

    nodes.push(node('done', 'screen', x, 80, { screen: 'done' }))
    edges.push(edge(`e${eid++}`, prev, 'done', 'next'))

    if (includePrinter && includeInterests) {
      nodes.push(node('printer', 'integration', x, 280, { kind: 'printer' }))
      edges.push(edge(`e${eid++}`, 'interests', 'printer', 'print_label'))
    } else if (includePrinter) {
      nodes.push(node('printer', 'integration', x, 280, { kind: 'printer' }))
      edges.push(edge(`e${eid++}`, 'done', 'printer', 'print_label'))
    }
  }

  if (includeCheckout) {
    nodes.push(node('qr', 'screen', 300, 340, { screen: 'qr_scan' }))
    nodes.push(node('demo_matched', 'screen', 540, 340, { screen: 'demo_matched' }))
    nodes.push(node('demo_done', 'screen', 780, 300, { screen: 'demo_done' }))
    nodes.push(node('checkout_done', 'screen', 780, 420, { screen: 'checkout_done' }))
    edges.push(edge(`e${eid++}`, 'start', 'qr', 'checkout'))
    edges.push(edge(`e${eid++}`, 'qr', 'demo_matched', 'next'))
    edges.push(edge(`e${eid++}`, 'demo_matched', 'demo_done', 'wants_demo'))
    edges.push(edge(`e${eid++}`, 'demo_matched', 'checkout_done', 'no_demo'))
  }

  // If only checkout and no register, still need start
  if (!includeRegister && !includeCheckout) {
    // Fallback: minimal register
    nodes.push(node('name', 'screen', 320, 80, { screen: 'name_input' }))
    nodes.push(node('done', 'screen', 560, 80, { screen: 'done' }))
    edges.push(edge(`e${eid++}`, 'start', 'name', 'register'))
    edges.push(edge(`e${eid++}`, 'name', 'done', 'next'))
    edges.push(edge(`e${eid++}`, 'name', 'db', 'lookup'))
  }

  return { nodes, edges }
}

export function boothModeFromAnswers(answers) {
  if (answers.includeRegister && answers.includeCheckout) return 'both'
  if (answers.includeRegister) return 'register'
  if (answers.includeCheckout) return 'demo'
  return 'both'
}
