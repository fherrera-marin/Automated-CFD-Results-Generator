# Operating the CFD pipeline app

## 1. One-time setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[web]"
copy backend\.env.example .env   # then edit the values below
cd backend
..\.venv\Scripts\python manage.py migrate
```

## 2. Required `.env` values (repo root)

| Variable | What it is | How to find it on this machine |
|---|---|---|
| `OPENFOAM_ENV_SCRIPT` | Batch file that activates OpenFOAM's environment (puts `blockMesh`, `snappyHexMesh`, `simpleFoam`, ... on `PATH`) | For this BlueCFD-Core-2020 install: `D:\Programa\blueCFD-Core-2020\setvars_OF8.bat`. On another machine, look for a `setvars_OF*.bat` or `DOS_Mode_OF*.bat` at the root of the blueCFD-Core install directory. |
| `PVBATCH_BIN` | ParaView's batch executable, used for the CSV export stage | For this install: `D:\Programa\blueCFD-Core-2020\AddOns\ParaView\bin\pvbatch.exe`. Generally under `<blueCFD-Core>\AddOns\ParaView\bin\`. |
| `FOAMTOVTK_BIN` | Name of the foamToVTK utility | `foamToVTK` (resolved through the activated OpenFOAM environment, same as the other 6 solver/utility steps). |
| `SIM_ORIGIN_DIR` | Default template OpenFOAM case copied into every generated case, when a Run doesn't specify its own `origin_dir` | No portable default — point it at your own template case (the one with `constant/triSurface/op1.stl` as the geometry snappyHexMesh snaps to). |
| `SIM_BASE_DIR` | Where generated runs live | Defaults to `<repo>/data/runs`; override only if you want simulations stored elsewhere. |
| `REDIS_URL` | Broker/result backend for Celery | `redis://localhost:6379/0` if running Redis locally. |

## 3. Starting everything (4 processes)

```powershell
redis-server                                                    # 1) broker
.venv\Scripts\celery -A config worker --pool=solo -Q default,cfd --loglevel=info   # 2) worker (from backend/)
.venv\Scripts\python manage.py runserver                        # 3) API (from backend/)
.tools\node-v24.22.1-win-x64\npm.cmd run dev                    # 4) frontend (from frontend/)
```

`--pool=solo` is required on Windows: Celery's default `prefork` pool does not work there.

### Frontend toolchain note

The system Node.js on this machine (`D:\Programa\node`, v12.19.0) is too old for
Vite/React. Rather than touching that install, a portable Node 24 LTS is
unpacked under `.tools/node-v24.22.1-win-x64/` (gitignored, not part of the
repo) and used only for this project:

```powershell
$env:PATH = "$PWD\.tools\node-v24.22.1-win-x64;$env:PATH"
cd frontend
npm install
npm run dev
```

### Port collision with another local project (WSL)

If `python manage.py runserver` (port 8000) or the Vite dev server (port
5173) ever serve content that isn't this app, check whether WSL2 is
forwarding those same ports from a guest service (seen on this machine: a
`wslrelay` process forwarding 8000/5173 to another project running inside
WSL). `Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | Select
LocalPort,OwningProcess` will show every PID actually bound to each port —
if `wslrelay` (or anything other than your own `python`/`node` process)
shows up, either stop the WSL service first or run this app's servers on
different ports (e.g. `runserver 127.0.0.1:8010`, `vite --port 5174`, and
point `vite.config.ts`'s proxy `target` at the port you chose).

## 4. Quirks discovered while integrating this on BlueCFD-Core-2020

These affect anyone adapting `src/simulation/openfoam_runner.py` or
`scripts/paraview_export_macro.py`, not just this one machine:

- **`setvars_OF8.bat` changes directory as a side effect.** It `cd`s into
  the blueCFD-Core install root before setting any environment variable.
  Chaining it directly before a real command (`cmd /c "setvars_OF8.bat" &&
  blockMesh`) would run `blockMesh` from the wrong working directory.
  `openfoam_runner.capture_env()` works around this by running the script
  once, capturing the resulting environment via `set`, and passing that
  captured `dict` as `env=` to every later `subprocess.run(..., cwd=case_dir)`
  call — the batch file's own `cd` never affects those later calls.

- **A custom `env=` dict does not change how Windows resolves a bare
  executable name.** `CreateProcess` searches the *calling* process's
  `PATH` to find `blockMesh.exe`, not the `env` dict handed to the child.
  `openfoam_runner.run_command()` resolves the executable itself with
  `shutil.which(name, path=env["PATH"])` before calling `subprocess.run`.

- **`foamToVTK` can fail on boundary patches with a valid OpenFOAM case.**
  snappyHexMesh can auto-generate patch group names containing a colon
  (e.g. `motorBike_frt-fairing:001%1`), which is an invalid Windows
  directory-name character; `foamToVTK` then exits non-zero after already
  writing the internal-field VTK file we actually need. `foam_to_vtk.py`
  passes `-excludePatches '(".*")'` to skip boundary patches entirely,
  since `paraview_export_macro.py` never reads them anyway.

- **`surfaceFeatures`/snappyHexMesh can crash (access violation, exit code
  `0xC0000005`) on long paths**, well past already finishing its real work
  (the crash in `surfaceFeatures` happened right after it printed
  "Writing extendedFeatureEdgeMesh to ..."). Reproduced reliably around
  ~288 characters for the deepest generated file path
  (`<case_dir>/constant/extendedFeatureEdgeMesh/op1.extendedFeatureEdgeMesh`),
  not reliably at the classic Windows `MAX_PATH` of 260 (275 chars worked,
  288 didn't) — this looks like a fixed-size internal buffer in this
  Windows build of the utility rather than a documented OS limit. Not an
  issue for `SIM_BASE_DIR`'s default (`<repo>/data/runs/...`, well under
  200 chars for a typical case path), but keep that setting short and
  avoid deeply nested paths (e.g. inside a OneDrive/Dropbox sync folder)
  if cases start failing `surfaceFeatures` or `snappyHexMesh` with no
  FOAM-level error message at all.

- **`pvbatch` on this install embeds Python 2.7** (ParaView 5.6.2), so
  `scripts/paraview_export_macro.py` has to stay Python-2.7-compatible: no
  f-strings, no `pathlib`. The original `scripts/macro.py`'s `1024L` long
  literal is exactly this kind of Python-2-only syntax, just one that
  happens to also be invalid in Python 3 — removing the `L` suffix fixes
  it for both.
