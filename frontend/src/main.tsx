import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient()

// HashRouter (not BrowserRouter): this app is meant to also run as a static
// build on GitHub Pages (see package.json's build:demo), which has no
// server to fall back unknown paths to index.html -- hash-based routes
// (#/runs/1) always resolve to the same static index.html with no extra
// server config needed, at the cost of the # in the URL.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <App />
      </HashRouter>
    </QueryClientProvider>
  </StrictMode>,
)
