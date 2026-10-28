import { Link, Route, Routes } from 'react-router-dom'
import DemoBanner from './components/DemoBanner'
import NewRunForm from './pages/NewRunForm'
import RunDetailPage from './pages/RunDetailPage'
import RunsListPage from './pages/RunsListPage'

// Files under public/ are served as-is, so referencing them with a plain
// "/foo.png" string (unlike imported assets) is NOT rewritten for the
// demo build's relative `base: './'` -- BASE_URL is, so prefix with it.
const logoSrc = `${import.meta.env.BASE_URL}ucm-logo-header.png`

export default function App() {
  return (
    <div className="app">
      <DemoBanner />
      <header className="app-header">
        <Link to="/" className="app-brand">
          <img src={logoSrc} alt="Universidad Complutense de Madrid" className="app-logo" />
          <span className="app-divider" aria-hidden="true" />
          <span className="app-titles">
            <span className="app-title">Automated CFD Results Generator</span>
            <span className="app-subtitle">Wind turbine airfoil simulation pipeline</span>
          </span>
        </Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<RunsListPage />} />
          <Route path="/runs/new" element={<NewRunForm />} />
          <Route path="/runs/:id" element={<RunDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
