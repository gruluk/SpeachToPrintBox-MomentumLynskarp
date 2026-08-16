/** Split / join event start as date + time stored in starts_at (YYYY-MM-DD or YYYY-MM-DDTHH:mm). */

export function splitStartsAt(value) {
  const raw = (value || '').trim()
  if (!raw) return { date: '', time: '' }
  if (raw.includes('T')) {
    const [datePart, timePart = ''] = raw.split('T')
    return {
      date: datePart.slice(0, 10),
      time: timePart.slice(0, 5),
    }
  }
  // Legacy: date-only, or "date time"
  const [datePart, timePart = ''] = raw.split(/\s+/)
  return {
    date: datePart.slice(0, 10),
    time: timePart.slice(0, 5),
  }
}

export function joinStartsAt(date, time) {
  const d = (date || '').trim().slice(0, 10)
  const t = (time || '').trim().slice(0, 5)
  if (!d) return ''
  if (!t) return d
  return `${d}T${t}`
}

/** Human-readable start for lists, e.g. "16.08.2026 kl. 09:00". */
export function formatStartsAt(value) {
  const { date, time } = splitStartsAt(value)
  if (!date) return ''
  const [y, m, d] = date.split('-')
  const nice = d && m && y ? `${d}.${m}.${y}` : date
  return time ? `${nice} kl. ${time}` : nice
}
