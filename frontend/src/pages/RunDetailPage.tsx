import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Fragment, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, IS_DEMO_MODE, STAGE_LABELS, STAGES, type StageName } from '../api/client'
import CaseFieldViewer from '../components/CaseFieldViewer'
import StatusBadge from '../components/StatusBadge'

const PER_CASE_STAGES = new Set<StageName>(['openfoam', 'foam_to_vtk', 'paraview_export'])

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const runId = Number(id)
  const queryClient = useQueryClient()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => api.getRun(runId) })

  const statusQuery = useQuery({
    queryKey: ['run-status', runId],
    queryFn: () => api.getStatus(runId),
    refetchInterval: 2500,
  })

  const casesQuery = useQuery({
    queryKey: ['run-cases', runId],
    queryFn: () => api.getCases(runId),
    refetchInterval: 2500,
  })

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['run', runId] })
    queryClient.invalidateQueries({ queryKey: ['run-status', runId] })
    queryClient.invalidateQueries({ queryKey: ['run-cases', runId] })
  }

  const startPipeline = useMutation({
    mutationFn: () => api.startPipeline(runId),
    onSuccess: invalidateAll,
  })
  const startStage = useMutation({
    mutationFn: (stage: StageName) => api.startStage(runId, stage),
    onSuccess: invalidateAll,
  })
  const retryFailed = useMutation({
    mutationFn: (stage: StageName) => api.retryFailed(runId, stage),
    onSuccess: invalidateAll,
  })
  const stopRun = useMutation({
    mutationFn: () => api.stop(runId),
    onSuccess: invalidateAll,
  })
  const [expandedCaseId, setExpandedCaseId] = useState<number | null>(null)

  if (runQuery.isLoading) return <p>Loading…</p>
  if (runQuery.error) return <p className="error-text">{(runQuery.error as Error).message}</p>
  const run = runQuery.data
  if (!run) return null

  const liveStatus = statusQuery.data?.status ?? run.status
  const stageStatus = statusQuery.data?.stages ?? run.stages
  const anyMutationPending =
    startPipeline.isPending || startStage.isPending || retryFailed.isPending || stopRun.isPending

  return (
    <div className="page">
      <div className="page-header">
        <h1>{run.name || `Run #${run.id}`}</h1>
        <StatusBadge status={liveStatus} />
      </div>

      <section className="card">
        <h2>Parameters</h2>
        <dl className="kv">
          <dt>N airfoils</dt>
          <dd>{run.n_airfoils}</dd>
          <dt>Angles</dt>
          <dd>{run.angles.join(', ')}</dd>
          <dt>Base dir</dt>
          <dd className="mono">{run.base_dir}</dd>
          <dt>Origin dir</dt>
          <dd className="mono">{run.origin_dir}</dd>
        </dl>
        {run.error_message && <p className="error-text">{run.error_message}</p>}
        <button
          className="btn btn-primary"
          onClick={() => startPipeline.mutate()}
          disabled={anyMutationPending || liveStatus === 'running' || IS_DEMO_MODE}
          title={IS_DEMO_MODE ? 'Disabled in the static demo -- run the real backend to try this.' : undefined}
        >
          Start full pipeline
        </button>
        <button
          className="btn btn-danger"
          onClick={() => stopRun.mutate()}
          disabled={anyMutationPending || liveStatus !== 'running' || IS_DEMO_MODE}
          title={
            IS_DEMO_MODE
              ? 'Disabled in the static demo -- run the real backend to try this.'
              : 'Kills the currently running OpenFOAM step immediately and cancels anything still pending.'
          }
        >
          Stop
        </button>
      </section>

      <section className="card">
        <h2>Stages</h2>
        <div className="stage-grid">
          {STAGES.map((stage) => {
            const info = stageStatus.find((s) => s.stage === stage)
            return (
              <div key={stage} className="stage-card">
                <div className="stage-card-header">
                  <strong>{STAGE_LABELS[stage]}</strong>
                  <StatusBadge status={info?.status ?? 'pending'} />
                </div>
                <div className="stage-card-actions">
                  <button
                    className="btn"
                    onClick={() => startStage.mutate(stage)}
                    disabled={anyMutationPending || IS_DEMO_MODE}
                    title={IS_DEMO_MODE ? 'Disabled in the static demo -- run the real backend to try this.' : undefined}
                  >
                    Start stage
                  </button>
                  {PER_CASE_STAGES.has(stage) && (
                    <button
                      className="btn"
                      onClick={() => retryFailed.mutate(stage)}
                      disabled={anyMutationPending || IS_DEMO_MODE}
                      title={IS_DEMO_MODE ? 'Disabled in the static demo -- run the real backend to try this.' : undefined}
                    >
                      Retry failed
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="card">
        <h2>Cases ({casesQuery.data?.length ?? 0})</h2>
        {casesQuery.data && casesQuery.data.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Angle</th>
                <th>OpenFOAM</th>
                <th>foamToVTK</th>
                <th>ParaView</th>
                <th>Results</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {casesQuery.data.map((c) => (
                <Fragment key={c.id}>
                  <tr>
                    <td>{c.name}</td>
                    <td>{c.angle}</td>
                    <td>
                      <StatusBadge status={c.openfoam_status} />
                      {c.openfoam_step && <span className="muted"> ({c.openfoam_step})</span>}
                    </td>
                    <td>
                      <StatusBadge status={c.foam_to_vtk_status} />
                    </td>
                    <td>
                      <StatusBadge status={c.paraview_export_status} />
                    </td>
                    <td>
                      <button
                        className="btn"
                        disabled={c.paraview_export_status !== 'done'}
                        onClick={() => setExpandedCaseId(expandedCaseId === c.id ? null : c.id)}
                        title={
                          c.paraview_export_status !== 'done'
                            ? 'Available once this case finishes the ParaView export stage.'
                            : undefined
                        }
                      >
                        {expandedCaseId === c.id ? 'Hide' : 'View results'}
                      </button>
                    </td>
                    <td className="error-text">{c.error_message}</td>
                  </tr>
                  {expandedCaseId === c.id && (
                    <tr>
                      <td colSpan={7}>
                        <CaseFieldViewer runId={runId} caseId={c.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No cases yet.</p>
        )}
      </section>

      <LogsPanel runId={runId} />

      <DatasetSection runId={runId} status={liveStatus} />
    </div>
  )
}

function LogsPanel({ runId }: { runId: number }) {
  const [sinceId, setSinceId] = useState<number | undefined>(undefined)
  const [entries, setEntries] = useState<import('../api/client').LogEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const logsQuery = useQuery({
    queryKey: ['run-logs', runId, sinceId],
    queryFn: () => api.getLogs(runId, sinceId),
    refetchInterval: 3000,
  })

  useEffect(() => {
    if (!logsQuery.data || logsQuery.data.length === 0) return
    setEntries((prev) => [...prev, ...logsQuery.data!])
    setSinceId(logsQuery.data[logsQuery.data.length - 1].id)
  }, [logsQuery.data])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [entries.length])

  return (
    <section className="card">
      <h2>Logs</h2>
      <div className="log-panel">
        {entries.length === 0 && <p className="muted">No log entries yet.</p>}
        {entries.map((entry) => (
          <div key={entry.id} className={`log-line log-${entry.level}`}>
            <span className="muted">[{entry.stage}]</span> {entry.message}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </section>
  )
}

function DatasetSection({ runId, status }: { runId: number; status: string }) {
  const datasetQuery = useQuery({
    queryKey: ['run-dataset', runId],
    queryFn: () => api.getDataset(runId),
    enabled: status === 'done',
    retry: false,
  })

  return (
    <section className="card">
      <h2>Dataset</h2>
      {status !== 'done' && <p className="muted">Available once the pipeline finishes.</p>}
      {status === 'done' && datasetQuery.data && (
        <>
          <dl className="kv">
            <dt>Path</dt>
            <dd className="mono">{datasetQuery.data.path}</dd>
            <dt>Size</dt>
            <dd>{(datasetQuery.data.size_bytes / 1024).toFixed(1)} KB</dd>
            <dt>Cases</dt>
            <dd>{datasetQuery.data.case_count}</dd>
          </dl>
          <a className="btn btn-primary" href={api.datasetDownloadUrl(runId)}>
            Download CNN_df.pkl
          </a>
        </>
      )}
    </section>
  )
}
