from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
import numpy as np

def compute_sdf(contour,
        airfoil_step: float = 0.002,
        # ------- angulos múltiples ------------
        # x_min: float = -1.5,
        #x_max: float = 1.5,
        #y_min: float = -1.5,
        #y_max: float = 1.5,
        #resolution_x: int = 256,
        #resolution_y: int = 256,

        # ------------ flujo paralelo ------------
        x_min: float = -0.5,
        x_max: float = 1.5,
        y_min: float = -0.5,
        y_max: float = 0.5,
        resolution_x: int = 200,
        resolution_y: int = 80,
        signed_distance: bool = True,
        inside_value: float = -1.0,
    ):
        """
        Compute a 2D Signed Distance Function (SDF) of the airfoil.

        Returns
        -------
        sdf : ndarray (resolution_y, resolution_x)
            Signed distance field.
        X, Y : ndarray
            Coordinate grids (useful for plotting).
        """
        x_points = contour[:, 0]
        y_points = contour[:, 1]

        polygon = Polygon(contour)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            raise ValueError("Invalid polygon generated from airfoil contour.")

        xs = np.linspace(x_min, x_max, resolution_x)
        ys = np.linspace(y_min, y_max, resolution_y)
        #X, Y = np.meshgrid(xs, ys)

        sdf = np.empty((resolution_y, resolution_x), dtype=float)

        for j in range(resolution_y):
            y = ys[j]
            for k in range(resolution_x):
                x = xs[k]
                point = Point(x, y)

                # Distance to discretized contour (same logic as original code)
                distances = np.sqrt((x - x_points)**2 + (y - y_points)**2)
                min_distance = float(np.min(distances))

                inside = polygon.contains(point)

                if inside:
                    if signed_distance:
                        sdf[j, k] = -1
                else:
                    sdf[j, k] = min_distance

        # Matrix inversion for correct visualization
        sdf = np.flipud(sdf)
        return sdf