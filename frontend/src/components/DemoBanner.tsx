import { IS_DEMO_MODE } from '../api/client'

const REPO_URL = import.meta.env.VITE_REPO_URL as string | undefined

export default function DemoBanner() {
  if (!IS_DEMO_MODE) return null
  return (
    <div className="demo-banner">
      Static demo with sample data — no backend here, so actions like creating or starting a run are
      disabled.{' '}
      {REPO_URL && (
        <>
          The code (Django + Celery + React) is on{' '}
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
          .
        </>
      )}
    </div>
  )
}
