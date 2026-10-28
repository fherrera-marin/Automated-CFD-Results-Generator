import type {
  CreateRunInput,
  DatasetMeta,
  FieldName,
  LogEntry,
  Run,
  RunsApi,
  RunStatusResponse,
  SimulationCase,
  StageName,
} from './types'

const API_BASE = '/api/runs'

interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed with status ${resp.status}`)
  }
  if (resp.status === 204) return undefined as T
  return resp.json() as Promise<T>
}

function unwrap<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results
}

export const realApi: RunsApi = {
  listRuns: async (): Promise<Run[]> => unwrap(await request<Paginated<Run> | Run[]>('/')),

  getRun: (id: number) => request<Run>(`/${id}/`),

  createRun: (data: CreateRunInput) => request<Run>('/', { method: 'POST', body: JSON.stringify(data) }),

  deleteRun: (id: number, purgeFiles = false) =>
    request<void>(`/${id}/${purgeFiles ? '?purge_files=true' : ''}`, { method: 'DELETE' }),

  startPipeline: (id: number) => request<{ detail: string }>(`/${id}/pipeline/start/`, { method: 'POST' }),

  stop: (id: number) =>
    request<{ detail: string; killed_pids: number[] }>(`/${id}/stop/`, { method: 'POST' }),

  startStage: (id: number, stage: StageName) =>
    request<{ detail: string }>(`/${id}/stages/${stage}/start/`, { method: 'POST' }),

  retryFailed: (id: number, stage: StageName) =>
    request<{ detail: string; reset_count: number }>(`/${id}/stages/${stage}/retry-failed/`, {
      method: 'POST',
    }),

  getStatus: (id: number) => request<RunStatusResponse>(`/${id}/status/`),

  getCases: async (id: number): Promise<SimulationCase[]> =>
    unwrap(await request<Paginated<SimulationCase> | SimulationCase[]>(`/${id}/cases/`)),

  getLogs: (id: number, sinceId?: number) =>
    request<LogEntry[]>(`/${id}/logs/${sinceId ? `?since_id=${sinceId}` : ''}`),

  getDataset: (id: number) => request<DatasetMeta>(`/${id}/dataset/`),

  datasetDownloadUrl: (id: number) => `${API_BASE}/${id}/dataset/download/`,

  caseFieldUrl: (runId: number, caseId: number, field: FieldName) =>
    `${API_BASE}/${runId}/cases/${caseId}/field/?field=${field}`,
}
