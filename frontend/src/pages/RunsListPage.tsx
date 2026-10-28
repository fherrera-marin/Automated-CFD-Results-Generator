import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function RunsListPage() {
  const { data: runs, isLoading, error } = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 5000,
  })

  return (
    <div className="page">
      <div className="page-header">
        <h1>Runs</h1>
        <Link to="/runs/new" className="btn btn-primary">
          New run
        </Link>
      </div>

      {isLoading && <p>Loading…</p>}
      {error && <p className="error-text">{(error as Error).message}</p>}

      {runs && runs.length === 0 && <p className="muted">No runs yet. Create one to get started.</p>}

      {runs && runs.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>N airfoils</th>
              <th>Angles</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{run.id}</td>
                <td>
                  <Link to={`/runs/${run.id}`}>{run.name || `Run #${run.id}`}</Link>
                </td>
                <td>{run.n_airfoils}</td>
                <td>{run.angles.join(', ')}</td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
