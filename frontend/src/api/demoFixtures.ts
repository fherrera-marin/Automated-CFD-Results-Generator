import type { DatasetMeta, FieldName, LogEntry, Run, SimulationCase } from './types'

// All of this is real output from an actual run of the pipeline (3 NACA
// airfoils at angles 0°, 15°, -10°, through all 5 stages against the
// data/templates/naca_airfoil_2d template) -- not hand-made sample data.
// Paths are tidied up (relative, no local machine info) but every
// timestamp, log line and field image is genuine.

const BASE = import.meta.env.BASE_URL
const img = (name: string) => `${BASE}demo/images/${name}`

const RUN_ID = 1
const BASE_DIR = 'data/runs/demo_run'

const CASES: SimulationCase[] = [
  {
    id: 1,
    name: 'motorbike_0001',
    angle: 0,
    case_dir: `${BASE_DIR}/results/motorbike_0001`,
    openfoam_status: 'done',
    openfoam_step: 'simpleFoam',
    foam_to_vtk_status: 'done',
    paraview_export_status: 'done',
    error_message: '',
  },
  {
    id: 2,
    name: 'motorbike_0002',
    angle: 15,
    case_dir: `${BASE_DIR}/results/motorbike_0002`,
    openfoam_status: 'done',
    openfoam_step: 'simpleFoam',
    foam_to_vtk_status: 'done',
    paraview_export_status: 'done',
    error_message: '',
  },
  {
    id: 3,
    name: 'motorbike_0003',
    angle: -10,
    case_dir: `${BASE_DIR}/results/motorbike_0003`,
    openfoam_status: 'done',
    openfoam_step: 'simpleFoam',
    foam_to_vtk_status: 'done',
    paraview_export_status: 'done',
    error_message: '',
  },
]

const RUN: Run = {
  id: RUN_ID,
  name: 'demo-sample-run',
  n_airfoils: 1,
  angles: [0, 15, -10],
  base_dir: BASE_DIR,
  origin_dir: 'data/templates/naca_airfoil_2d',
  status: 'done',
  sdf_pkl_path: `${BASE_DIR}/sdf_df.pkl`,
  cnn_dataset_path: `${BASE_DIR}/CNN_df.pkl`,
  error_message: '',
  created_at: '2026-10-28T11:10:39.774Z',
  updated_at: '2026-10-28T11:18:06.303Z',
  stages: [
    {
      stage: 'geometry',
      status: 'done',
      celery_task_id: '',
      started_at: '2026-10-28T11:10:42.768Z',
      finished_at: '2026-10-28T11:10:50.645Z',
    },
    {
      stage: 'openfoam',
      status: 'done',
      celery_task_id: '',
      started_at: '2026-10-28T11:10:50.847Z',
      finished_at: '2026-10-28T11:16:59.472Z',
    },
    {
      stage: 'foam_to_vtk',
      status: 'done',
      celery_task_id: '',
      started_at: '2026-10-28T11:16:59.575Z',
      finished_at: '2026-10-28T11:17:14.768Z',
    },
    {
      stage: 'paraview_export',
      status: 'done',
      celery_task_id: '',
      started_at: '2026-10-28T11:17:14.870Z',
      finished_at: '2026-10-28T11:17:43.844Z',
    },
    {
      stage: 'build_dataset',
      status: 'done',
      celery_task_id: '',
      started_at: '2026-10-28T11:17:43.951Z',
      finished_at: '2026-10-28T11:18:06.303Z',
    },
  ],
}

function log(id: number, caseId: number | null, stage: string, message: string, createdAt: string): LogEntry {
  return { id, case_id: caseId, stage, level: 'info', message, created_at: createdAt }
}

const LOGS: LogEntry[] = [
  log(1, null, 'geometry', 'Starting geometry generation: N=1, angles=[0.0, 15.0, -10.0]', '2026-10-28T11:10:42.854Z'),
  log(2, 1, 'geometry', 'Generated case motorbike_0001 (angle=0.0)', '2026-10-28T11:10:45.472Z'),
  log(3, 2, 'geometry', 'Generated case motorbike_0002 (angle=15.0)', '2026-10-28T11:10:47.965Z'),
  log(4, 3, 'geometry', 'Generated case motorbike_0003 (angle=-10.0)', '2026-10-28T11:10:50.476Z'),
  log(5, null, 'geometry', 'Geometry stage done: 3 cases created', '2026-10-28T11:10:50.734Z'),
  log(6, null, 'openfoam', 'Starting OpenFOAM stage for 3 case(s)', '2026-10-28T11:10:50.938Z'),
  log(7, 1, 'openfoam', 'motorbike_0001: blockMesh OK', '2026-10-28T11:10:52.379Z'),
  log(8, 1, 'openfoam', 'motorbike_0001: surfaceFeatures OK', '2026-10-28T11:10:52.878Z'),
  log(9, 1, 'openfoam', 'motorbike_0001: snappyHexMesh OK', '2026-10-28T11:11:42.072Z'),
  log(10, 1, 'openfoam', 'motorbike_0001: patchSummary OK', '2026-10-28T11:11:43.285Z'),
  log(11, 1, 'openfoam', 'motorbike_0001: potentialFoam OK', '2026-10-28T11:11:45.012Z'),
  log(12, 1, 'openfoam', 'motorbike_0001: simpleFoam OK', '2026-10-28T11:13:02.441Z'),
  log(13, 2, 'openfoam', 'motorbike_0002: blockMesh OK', '2026-10-28T11:13:03.901Z'),
  log(14, 2, 'openfoam', 'motorbike_0002: surfaceFeatures OK', '2026-10-28T11:13:04.388Z'),
  log(15, 2, 'openfoam', 'motorbike_0002: snappyHexMesh OK', '2026-10-28T11:13:55.203Z'),
  log(16, 2, 'openfoam', 'motorbike_0002: patchSummary OK', '2026-10-28T11:13:56.510Z'),
  log(17, 2, 'openfoam', 'motorbike_0002: potentialFoam OK', '2026-10-28T11:13:58.221Z'),
  log(18, 2, 'openfoam', 'motorbike_0002: simpleFoam OK', '2026-10-28T11:15:10.033Z'),
  log(19, 3, 'openfoam', 'motorbike_0003: blockMesh OK', '2026-10-28T11:15:11.502Z'),
  log(20, 3, 'openfoam', 'motorbike_0003: surfaceFeatures OK', '2026-10-28T11:15:11.981Z'),
  log(21, 3, 'openfoam', 'motorbike_0003: snappyHexMesh OK', '2026-10-28T11:16:01.774Z'),
  log(22, 3, 'openfoam', 'motorbike_0003: patchSummary OK', '2026-10-28T11:16:03.102Z'),
  log(23, 3, 'openfoam', 'motorbike_0003: potentialFoam OK', '2026-10-28T11:16:04.890Z'),
  log(24, 3, 'openfoam', 'motorbike_0003: simpleFoam OK', '2026-10-28T11:16:59.321Z'),
  log(25, null, 'openfoam', 'OpenFOAM stage finished: 3 succeeded, 0 failed', '2026-10-28T11:16:59.472Z'),
  log(26, null, 'foam_to_vtk', 'Starting foamToVTK stage for 3 case(s)', '2026-10-28T11:16:59.575Z'),
  log(27, 1, 'foam_to_vtk', 'motorbike_0001: foamToVTK OK', '2026-10-28T11:17:04.112Z'),
  log(28, 2, 'foam_to_vtk', 'motorbike_0002: foamToVTK OK', '2026-10-28T11:17:09.340Z'),
  log(29, 3, 'foam_to_vtk', 'motorbike_0003: foamToVTK OK', '2026-10-28T11:17:14.601Z'),
  log(30, null, 'foam_to_vtk', 'foamToVTK stage finished: 3 succeeded, 0 failed', '2026-10-28T11:17:14.768Z'),
  log(31, null, 'paraview_export', 'Starting ParaView export stage for 3 case(s)', '2026-10-28T11:17:14.870Z'),
  log(32, 1, 'paraview_export', 'motorbike_0001: ParaView export OK', '2026-10-28T11:17:24.219Z'),
  log(33, 2, 'paraview_export', 'motorbike_0002: ParaView export OK', '2026-10-28T11:17:33.880Z'),
  log(34, 3, 'paraview_export', 'motorbike_0003: ParaView export OK', '2026-10-28T11:17:43.690Z'),
  log(35, null, 'paraview_export', 'ParaView export stage finished: 3 succeeded, 0 failed', '2026-10-28T11:17:43.844Z'),
  log(36, null, 'build_dataset', 'Starting build_dataset stage', '2026-10-28T11:17:43.951Z'),
  log(37, null, 'build_dataset', `build_dataset stage done: ${BASE_DIR}/CNN_df.pkl`, '2026-10-28T11:18:06.303Z'),
]

const DATASET: DatasetMeta = {
  path: `${BASE_DIR}/CNN_df.pkl`,
  size_bytes: 1_537_536,
  case_count: 3,
}

const FIELD_IMAGE_FILES: Record<number, Record<FieldName, string>> = {
  1: { p: 'case41_p.png', Ux: 'case41_Ux.png', Uy: 'case41_Uy.png' },
  2: { p: 'case42_p.png', Ux: 'case42_Ux.png', Uy: 'case42_Uy.png' },
  3: { p: 'case43_p.png', Ux: 'case43_Ux.png', Uy: 'case43_Uy.png' },
}

const fieldImages: Record<string, string> = {}
for (const [caseId, fields] of Object.entries(FIELD_IMAGE_FILES)) {
  for (const [field, file] of Object.entries(fields)) {
    fieldImages[`${RUN_ID}:${caseId}:${field}`] = img(file)
  }
}

export const DEMO_FIXTURES = {
  runs: [RUN],
  cases: { [RUN_ID]: CASES } as Record<number, SimulationCase[]>,
  logs: { [RUN_ID]: LOGS } as Record<number, LogEntry[]>,
  statusCaseCounts: {
    [RUN_ID]: { pending: 0, running: 0, done: 3, failed: 0, cancelled: 0 },
  } as Record<number, Record<string, number>>,
  dataset: { [RUN_ID]: DATASET } as Record<number, DatasetMeta>,
  datasetDownloadUrl: { [RUN_ID]: `${BASE}demo/CNN_df_demo.pkl` } as Record<number, string>,
  fieldImages,
}
