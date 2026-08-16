/** Resolve next screen node id from flow graph given current node + action. */
export function nextNodeId(flow, currentId, action) {
  if (!flow?.edges) return null
  const edge = flow.edges.find(
    (e) => e.source === currentId && (e.data?.action || 'next') === action,
  )
  return edge?.target || null
}

export function nodeById(flow, nodeId) {
  return flow?.nodes?.find((n) => n.id === nodeId) || null
}

export function nodeScreen(flow, nodeId) {
  const node = nodeById(flow, nodeId)
  if (!node || node.type === 'integration') return null
  return node.data?.screen || null
}

export function nodeKind(flow, nodeId) {
  const node = nodeById(flow, nodeId)
  return node?.data?.kind || null
}

/** Follow action, skipping integration/entry modules via their `next` edge. */
export function resolveActionTarget(flow, currentId, action) {
  let id = nextNodeId(flow, currentId, action)
  for (let i = 0; i < 8 && id; i += 1) {
    const scr = nodeScreen(flow, id)
    if (scr) return id
    // Integration / entry module — continue along next
    id = nextNodeId(flow, id, 'next') || nextNodeId(flow, id, action)
  }
  return null
}

export function hasAction(flow, currentId, action) {
  return Boolean(resolveActionTarget(flow, currentId, action))
}

export function hasModule(flow, kind) {
  return Boolean(flow?.nodes?.some((n) => n.data?.kind === kind))
}

/** Parse /e/{slug}/booth/{n} or legacy /booth/{n} */
export function parseBoothLocation(pathname = window.location.pathname) {
  let match = pathname.match(/\/e\/([^/]+)\/booth\/(\d+)/)
  if (match) {
    return { eventSlug: match[1], boothNumber: parseInt(match[2], 10) }
  }
  match = pathname.match(/\/booth\/(\d+)/)
  if (match) {
    return { eventSlug: 'lynskarp', boothNumber: parseInt(match[1], 10) }
  }
  return { eventSlug: 'lynskarp', boothNumber: 1 }
}

export function apiBase(eventSlug) {
  return `/e/${eventSlug}`
}
