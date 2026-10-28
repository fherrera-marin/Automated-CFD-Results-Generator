import { DEMO_FIXTURES } from './demoFixtures'
import { DEMO_DISABLED_MESSAGE, type FieldName, type Run, type RunsApi } from './types'

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function disabled(): Promise<never> {
  return Promise.reject(new Error(DEMO_DISABLED_MESSAGE))
}

function findRun(id: number): Run {
  const run = DEMO_FIXTURES.runs.find((r) => r.id === id)
  if (!run) throw new Error(`Demo run ${id} not found.`)
  return run
}

export const demoApi: RunsApi = {
  listRuns: async () => clone(DEMO_FIXTURES.runs),

  getRun: async (id) => clone(findRun(id)),

  createRun: () => disabled(),
  deleteRun: () => disabled(),
  startPipeline: () => disabled(),
  stop: () => disabled(),
  startStage: () => disabled(),
  retryFailed: () => disabled(),

  getStatus: async (id) => {
    const run = findRun(id)
    return clone({
      id: run.id,
      status: run.status,
      error_message: run.error_message,
      stages: run.stages.map(({ stage, status, started_at, finished_at }) => ({
        stage,
        status,
        started_at,
        finished_at,
      })),
      case_counts: DEMO_FIXTURES.statusCaseCounts[id] ?? {},
      total_cases: (DEMO_FIXTURES.cases[id] ?? []).length,
    })
  },

  getCases: async (id) => clone(DEMO_FIXTURES.cases[id] ?? []),

  getLogs: async (id, sinceId) => {
    const logs = DEMO_FIXTURES.logs[id] ?? []
    return clone(sinceId ? logs.filter((l) => l.id > sinceId) : logs)
  },

  getDataset: async (id) => {
    const meta = DEMO_FIXTURES.dataset[id]
    if (!meta) throw new Error('Dataset not available for this demo run.')
    return clone(meta)
  },

  datasetDownloadUrl: (id) => DEMO_FIXTURES.datasetDownloadUrl[id] ?? '#',

  caseFieldUrl: (runId, caseId, field: FieldName) =>
    DEMO_FIXTURES.fieldImages[`${runId}:${caseId}:${field}`] ?? '',
}
