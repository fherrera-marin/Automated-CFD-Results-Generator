# Automated CFD Results Generator

A web app that turns a 100%-manual CFD workflow (run scripts one by one from an
OpenFOAM console, by hand, for every airfoil) into a one-click pipeline: generate
random NACA airfoils, mesh and simulate them in OpenFOAM, post-process the results
in ParaView, and assemble a labeled dataset ready to train a CNN surrogate model —
all orchestrated from a React UI with live progress, logs, and per-case field
visualization.

**Live demo:** _add the link here once GitHub Pages is live_ — sample data,
no backend, see [Live demo](#live-demo) below for how it's built/deployed.

## What it does

```
Generate N random NACA airfoils, rotated across a set of angles
        │  (geometry.random_airfoil_generator + CadQuery)
        ▼
Mesh + solve each case in OpenFOAM
        │  (blockMesh → surfaceFeatures → snappyHexMesh → patchSummary → potentialFoam → simpleFoam)
        ▼
Convert results to VTK                    (foamToVTK)
        ▼
Export a 2D slice (p, U) to CSV           (pvbatch + a ParaView macro)
        ▼
Build the final labeled dataset            (SDF + Ux/Uy/p, interpolated onto a
        (CNN_df.pkl)                        shared grid, ready for a CNN surrogate)
```

Each stage runs as a Celery task and can be started individually, retried per
failed case, or stopped mid-run — including killing the actual OpenFOAM
subprocess, not just marking it cancelled in the database.

## Why this exists

The original project was a research pipeline: a Tkinter GUI generated airfoil
geometry, and the rest (OpenFOAM simulation, ParaView export, dataset assembly)
was a handful of scripts run manually, one after another, from a BlueCFD
console. This project rebuilds that pipeline as a proper web app — same
underlying science, but orchestrated, resumable, and observable instead of
"run this script, wait, run the next one."

## Architecture

- **Frontend**: React + TypeScript + Vite, polling a REST API for live
  progress (no WebSockets needed at this scale).
- **Backend**: Django + Django REST Framework.
- **Task queue**: Celery + Redis, one task per pipeline stage and one task
  per simulation case within a stage (`chord`/`group`), so cases run
  independently and a single failure doesn't abort the batch.
- **CFD engine**: OpenFOAM via BlueCFD-Core (Windows), ParaView's `pvbatch`
  for post-processing — these run locally; see [Running it locally](#running-it-locally).

```
React (Vite) ──HTTP──▶ Django REST API ──▶ Celery worker ──▶ OpenFOAM / ParaView
                              │                                  (subprocess,
                              └──────────── Redis ───────────┘    local install)
```

## Notable engineering problems solved along the way

This pipeline runs real engineering software (OpenFOAM, ParaView) from a
Windows web backend, which surfaced a handful of non-obvious problems:

- **Celery can't cleanly kill one in-flight task on Windows.** The required
  `--pool=solo` runs everything in a single process, so
  `revoke(terminate=True)` would kill the whole worker. The Stop button
  instead tracks the OS-level PID of the currently-running OpenFOAM
  subprocess and kills that directly (`taskkill /T`).
- **BlueCFD's environment-activation script changes directory as a side
  effect**, so it can't be chained directly before a real command. The
  environment is captured once (via `set`) and reused as `env=` on every
  subsequent subprocess call instead.
- **A custom `env=` dict doesn't change how Windows resolves a bare
  executable name** — `CreateProcess` still searches the calling process's
  own `PATH`. Each OpenFOAM executable is resolved explicitly with
  `shutil.which(name, path=captured_env["PATH"])` first.
- **`surfaceFeatures` crashes (access violation) on long file paths** —
  reproduced around ~288 characters for the deepest generated file, not at
  the documented Windows `MAX_PATH`. Simulation output paths are kept short
  by default for this reason.
- **`pvbatch` embeds its own Python 2.7**, so the ParaView export macro has
  to stay Python-2/3-compatible (no f-strings, no `pathlib`).
- **Celery's actual built-in default queue is named `"celery"`, not
  `"default"`** — tasks not explicitly routed were silently queued
  somewhere the worker never listened, until `CELERY_TASK_DEFAULT_QUEUE`
  was set explicitly.
- A dataset-generation bug ported from the original research script (a
  256×256 discretization grid no longer matching the SDF's actual 80×200
  grid, which raises a numpy shape-mismatch error) was found and fixed
  while integrating it.

See [`docs/operations.md`](docs/operations.md) for the full write-up and how
to reproduce/diagnose each of these.

## Project structure

```
backend/            Django project (REST API, Celery tasks, models)
frontend/           React + TypeScript + Vite app
src/
  geometry/          NACA 4-digit airfoil generation, SDF, STL export
  simulation/         OpenFOAM subprocess orchestration
  postprocessing/     foamToVTK, ParaView export, dataset assembly, field preview images
scripts/             Standalone scripts that need a different Python runtime
                     (ParaView's embedded pvbatch Python) than the rest of the project
data/templates/      Example OpenFOAM case template (2D NACA airfoil, simpleFoam + snappyHexMesh)
docs/operations.md   Local setup, environment variables, and the issues above in detail
```

## Running it locally

This needs a real OpenFOAM + ParaView install (via BlueCFD-Core on Windows)
to actually run simulations — see [`docs/operations.md`](docs/operations.md)
for the full setup (Python/Node toolchains, Redis, environment variables,
starting all four processes).

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[web]"
copy backend\.env.example .env   # fill in OPENFOAM_ENV_SCRIPT, PVBATCH_BIN, SIM_ORIGIN_DIR
cd backend
..\.venv\Scripts\python manage.py migrate
```

Then start Redis, the Celery worker, the Django API, and the Vite dev
server as described in `docs/operations.md`.

## Live demo

`frontend/` can also be built as a static site with pre-loaded sample data
(real simulation output — no backend required) and deployed to GitHub
Pages:

```
npm run build:demo   # frontend/, outputs frontend/dist
```

A GitHub Actions workflow (`.github/workflows/deploy-demo.yml`) builds and
publishes this automatically on push to `main`.

## License

MIT — see [`LICENSE`](LICENSE).
