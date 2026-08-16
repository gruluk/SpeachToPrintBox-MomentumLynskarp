/** Resolve next screen node id from flow graph given current node + action. */
export function nextNodeId(flow, currentId, action) {
  if (!flow?.edges) return null
  const edge = flow.edges.find(
    (e) => e.source === currentId && (e.data?.action || 'next') === action,
  )
  return edge?.target || null
}

export function nodeScreen(flow, nodeId) {
  const node = flow?.nodes?.find((n) => n.id === nodeId)
  if (!node || node.type === 'integration') return null
  return node.data?.screen || null
}

export function hasAction(flow, currentId, action) {
  return Boolean(nextNodeId(flow, currentId, action))
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
