async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    throw new Error('Unauthorized — refresh and log in again')
  }
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const detail = data?.detail || data || res.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

export const api = {
  listEvents: () => request('/admin/api/events'),
  createEvent: (body) => request('/admin/api/events', { method: 'POST', body: JSON.stringify(body) }),
  getEvent: (id) => request(`/admin/api/events/${id}`),
  patchEvent: (id, body) =>
    request(`/admin/api/events/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteEvent: (id) => request(`/admin/api/events/${id}`, { method: 'DELETE' }),

  listUsers: (eventId) => request(`/admin/api/events/${eventId}/users`),
  addUser: (eventId, body) =>
    request(`/admin/api/events/${eventId}/users`, { method: 'POST', body: JSON.stringify(body) }),
  patchUser: (eventId, userId, body) =>
    request(`/admin/api/events/${eventId}/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  deleteUser: (eventId, userId) =>
    request(`/admin/api/events/${eventId}/users/${userId}`, { method: 'DELETE' }),
  importUsers: (eventId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request(`/admin/api/events/${eventId}/import-users`, { method: 'POST', body: fd })
  },
  clearRegistrations: (eventId) =>
    request(`/admin/api/events/${eventId}/clear-registrations`, { method: 'POST' }),
  deleteAllUsers: (eventId) =>
    request(`/admin/api/events/${eventId}/delete-all-users`, { method: 'POST' }),

  listBooths: (eventId) => request(`/admin/api/events/${eventId}/booths`),
  createBooth: (eventId) =>
    request(`/admin/api/events/${eventId}/booths`, { method: 'POST' }),
  patchBooth: (eventId, boothId, body) =>
    request(`/admin/api/events/${eventId}/booths/${boothId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  deleteBooth: (eventId, boothId) =>
    request(`/admin/api/events/${eventId}/booths/${boothId}`, { method: 'DELETE' }),
}
