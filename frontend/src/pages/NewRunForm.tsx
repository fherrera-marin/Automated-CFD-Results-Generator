import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, IS_DEMO_MODE } from '../api/client'

export default function NewRunForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [nAirfoils, setNAirfoils] = useState('10')
  const [angles, setAngles] = useState('0,45,90,135,180,225,270,315')
  const [originDir, setOriginDir] = useState('')
  const [baseDir, setBaseDir] = useState('')

  const createRun = useMutation({
    mutationFn: () =>
      api.createRun({
        name,
        n_airfoils: Number(nAirfoils),
        angles,
        origin_dir: originDir || undefined,
        base_dir: baseDir || undefined,
      }),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      navigate(`/runs/${run.id}`)
    },
  })

  return (
    <div className="page">
      <h1>New run</h1>
      {IS_DEMO_MODE && (
        <p className="error-text">
          This is a static demo deployment with no backend — submitting here won't create a real run.
          Open one of the pre-loaded example runs from the list instead.
        </p>
      )}
      <p className="muted">
        Paths below are resolved by the Django backend / Celery worker's filesystem, not your
        browser — make sure they're reachable from wherever those processes run.
      </p>

      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault()
          createRun.mutate()
        }}
      >
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="optional" />
        </label>

        <label>
          N (airfoils)
          <input
            type="number"
            min={1}
            value={nAirfoils}
            onChange={(event) => setNAirfoils(event.target.value)}
            required
          />
        </label>

        <label>
          Angles (deg)
          <input
            value={angles}
            onChange={(event) => setAngles(event.target.value)}
            placeholder="0, 45, 90"
            required
          />
        </label>

        <label>
          Origin (template) directory
          <input
            value={originDir}
            onChange={(event) => setOriginDir(event.target.value)}
            placeholder="leave blank to use the server's SIM_ORIGIN_DIR default"
          />
        </label>

        <label>
          Base directory <span className="muted">(optional)</span>
          <input
            value={baseDir}
            onChange={(event) => setBaseDir(event.target.value)}
            placeholder="leave blank to auto-generate under SIM_BASE_DIR"
          />
        </label>

        {createRun.isError && <p className="error-text">{(createRun.error as Error).message}</p>}

        <button type="submit" className="btn btn-primary" disabled={createRun.isPending}>
          {createRun.isPending ? 'Creating…' : 'Create run'}
        </button>
      </form>
    </div>
  )
}
