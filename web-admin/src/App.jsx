import { Routes, Route, Navigate } from 'react-router-dom'
import EventList from './pages/EventList'
import EventWorkspace from './pages/EventWorkspace'
import CreateEventWizard from './pages/CreateEventWizard'

export default function App() {
  return (
    <div className="layout">
      <Routes>
        <Route path="/" element={<EventList />} />
        <Route path="/new" element={<CreateEventWizard />} />
        <Route path="/events/:eventId/*" element={<EventWorkspace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
