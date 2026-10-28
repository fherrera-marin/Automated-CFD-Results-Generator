# NACA 4-Digit Airfoil Generator

This module provides a Python implementation of the classical **NACA 4-digit airfoil geometry**, enabling:

- Computation of airfoil coordinates from analytical definitions
- Visualization of the airfoil profile
- Generation of a 3D extruded solid
- Export to STL format for CFD meshing or CAD workflows

The implementation is intended for aerodynamic preprocessing within the context of
CFD simulations and surrogate modeling of wind turbine blade sections.

---

## Implemented Airfoil Definition

The airfoil geometry follows the standard NACA 4-digit formulation:

- **M**: maximum camber (first digit, % of chord)
- **P**: position of maximum camber (second digit, tenths of chord)
- **T**: maximum thickness (last two digits, % of chord)

Example:  
`NACA 2412` → M = 2%, P = 0.4, T = 12%

Both **closed** and **open trailing edge** configurations are supported.

---

## Usage Example

```python
from geometry.naca4 import NACA4Airfoil
from geometry.plot import AirfoilPlotter
from geometry.export_stl import export_from_contour

airfoil = NACA4Airfoil.from_code("2412", closed_te=True)
contour = airfoil.coordinates(step=0.01)

# Plot airfoil geometry
AirfoilPlotter.plot_contour(contour, title="NACA 2412")

# Export extruded STL geometry
export_from_contour(
    contour=contour,
    filename="naca2412.stl",
    thickness=0.5,
)
```

## Module layout

- `naca4.py` — `NACA4Airfoil`: analytical coordinates + 2D signed distance field.
- `transform.py` — `AirfoilTransform.rotate(...)`: rotate a contour by an angle of attack.
- `export_stl.py` — `export_from_contour(...)`: extrude a 2D contour into a 3D STL solid (via CadQuery).
- `plot.py` — `AirfoilPlotter`: matplotlib helpers for visualizing contours.
- `sdf.py` — standalone `compute_sdf(...)` function (same signed-distance logic as `NACA4Airfoil.compute_sdf`, used by the dataset generation pipeline).
- `random_airfoil_generator.py` — `generator(...)` / `generator_with_progress(...)`: the actual dataset-generation entry points used by the web app's geometry stage.
