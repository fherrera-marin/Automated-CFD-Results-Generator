import numpy as np
import cadquery as cq
from cadquery import exporters
from pathlib import Path

def export_from_contour(
        contour: np.ndarray,
        filename: str,
        thickness: float = 0.5,
        workplane: str = "XY",
        ensure_closed: bool = True,
        output_dir: str | Path | None = None,
    ) -> Path:
        """
        Export an STL from a 2D contour by extruding it.

        Parameters
        ----------
        contour : np.ndarray
            Nx2 array of [x, y] points describing the airfoil contour.
        filename : str
            Output STL file name (e.g., "naca2412.stl").
        thickness : float
            Extrusion thickness.
        workplane : str
            CadQuery workplane (default "XY").
        ensure_closed : bool
            If True, closes the polyline before extrusion.
        output_dir : str | Path | None
            Directory where the STL will be generated.
            If None, the project root (current working directory) is used.

        Returns
        -------
        Path
            Full path to the generated STL file.
        """

        pts = np.asarray(contour, dtype=float)

        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("contour must be an Nx2 array")

        if len(pts) < 3:
            raise ValueError("contour must contain at least 3 points")

        if thickness <= 0:
            raise ValueError("thickness must be > 0")

        # Resolve output directory
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / filename

        # CadQuery expects (x, y) tuples
        pts_list = [(float(x), float(y)) for x, y in pts]

        wp = cq.Workplane(workplane).polyline(pts_list)

        if ensure_closed:
            wp = wp.close()

        solid = wp.extrude(thickness)

        # ascii=True: OpenFOAM's surfaceFeatures crashes (access violation)
        # on this machine's BlueCFD build when reading CadQuery's default
        # binary STL output. ASCII avoids that binary-parser path entirely.
        exporters.export(solid, str(output_path), opt={"ascii": True})

        return output_path

