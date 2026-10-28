export type RunStatusValue = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'
export type StageName = 'geometry' | 'openfoam' | 'foam_to_vtk' | 'paraview_export' | 'build_dataset'
export type FieldName = 'p' | 'Ux' | 'Uy'

export const STAGES: StageName[] = ['geometry', 'openfoam', 'foam_to_vtk', 'paraview_export', 'build_dataset']

export const STAGE_LABELS: Record<StageName, string> = {
  geometry: 'Geometry generation',
  openfoam: 'OpenFOAM simulation',
  foam_to_vtk: 'foamToVTK conversion',
  paraview_export: 'ParaView CSV export',
  build_dataset: 'Build CNN dataset',
}

export const FIELD_LABELS: Record<FieldName, string> = {
  p: 'Pressure (p)',
  Ux: 'Velocity Ux',
  Uy: 'Velocity Uy',
}

export interface RunStage {
  stage: StageName
  status: RunStatusValue
  celery_task_id: string
  started_at: string | null
  finished_at: string | null
}

export interface Run {
  id: number
  name: string
  n_airfoils: number
  angles: number[]
  base_dir: string
  origin_dir: string
  status: RunStatusValue
  sdf_pkl_path: string
  cnn_dataset_path: string
  error_message: string
  created_at: string
  updated_at: string
  stages: RunStage[]
}

export interface SimulationCase {
  id: number
  name: string
  angle: number
  case_dir: string
  openfoam_status: RunStatusValue
  openfoam_step: string
  foam_to_vtk_status: RunStatusValue
  paraview_export_status: RunStatusValue
  error_message: string
}

export interface LogEntry {
  id: number
  case_id: number | null
  stage: string
  level: 'info' | 'warning' | 'error'
  message: string
  created_at: string
}

export interface RunStatusResponse {
  id: number
  status: RunStatusValue
  error_message: string
  stages: Pick<RunStage, 'stage' | 'status' | 'started_at' | 'finished_at'>[]
  case_counts: Record<string, number>
  total_cases: number
}

export interface DatasetMeta {
  path: string
  size_bytes: number
  case_count: number
}

export interface CreateRunInput {
  name: string
  n_airfoils: number
  angles: string
  origin_dir?: string
  base_dir?: string
}

export interface RunsApi {
  listRuns: () => Promise<Run[]>
  getRun: (id: number) => Promise<Run>
  createRun: (data: CreateRunInput) => Promise<Run>
  deleteRun: (id: number, purgeFiles?: boolean) => Promise<void>
  startPipeline: (id: number) => Promise<{ detail: string }>
  stop: (id: number) => Promise<{ detail: string; killed_pids: number[] }>
  startStage: (id: number, stage: StageName) => Promise<{ detail: string }>
  retryFailed: (id: number, stage: StageName) => Promise<{ detail: string; reset_count: number }>
  getStatus: (id: number) => Promise<RunStatusResponse>
  getCases: (id: number) => Promise<SimulationCase[]>
  getLogs: (id: number, sinceId?: number) => Promise<LogEntry[]>
  getDataset: (id: number) => Promise<DatasetMeta>
  datasetDownloadUrl: (id: number) => string
  caseFieldUrl: (runId: number, caseId: number, field: FieldName) => string
}

export const DEMO_DISABLED_MESSAGE =
  'This is a static demo deployment (GitHub Pages) with pre-loaded sample data. ' +
  'Write actions need the real Django/Celery backend -- clone the repo and run it locally to try them.'
