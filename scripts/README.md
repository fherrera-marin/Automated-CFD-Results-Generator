# scripts/

Standalone scripts that can't live inside the installable `src/` package
because they need a different Python interpreter than the rest of the
project:

- **`plot_airfoil.py`** — quick visual smoke test of the geometry package
  (`geometry.naca4` + `geometry.plot`): generates a NACA 2512 airfoil and
  plots its contour and signed-distance field. Run with the project's own
  venv: `python scripts/plot_airfoil.py`.

- **`paraview_export_macro.py`** — exports a 2D slice (`p`, `U`) of one
  OpenFOAM case's latest VTK timestep to CSV. Invoked by the Django backend
  (`backend/apps/runs/tasks.py::run_paraview_export_case`) via `pvbatch`,
  ParaView's own batch executable — **not** importable from this project's
  venv, since `pvbatch` embeds its own Python (see `docs/operations.md` for
  the version quirks that follow from that). Manual usage:

  ```
  pvbatch paraview_export_macro.py --case-dir <case> --output <case>/postProcessing/resultados.csv
  ```

The rest of the former manual pipeline (generate dataset → run OpenFOAM →
foamToVTK → ParaView export → build the training dataset) is now
orchestrated by the web app in `backend/` + `src/`; see the root `README.md`.
