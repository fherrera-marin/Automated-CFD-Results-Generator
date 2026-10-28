import numpy as np

class AirfoilTransform:
    """Geometric transformations for airfoil point sets."""

    @staticmethod
    def rotate(points: np.ndarray, angle_deg: float, center=(0.0, 0.0)) -> np.ndarray:
        """
        Rotate points by angle_deg degrees around a given center.

        Parameters
        ----------
        points : np.ndarray
            Nx2 array of (x, y) points.
        angle_deg : float
            Rotation angle in degrees (counter-clockwise).
        center : tuple
            Rotation center (cx, cy).

        Returns
        -------
        np.ndarray
            Rotated Nx2 array.
        """
        pts = np.asarray(points, dtype=float)

        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("points must be an Nx2 array")

        cx, cy = center
        angle = np.deg2rad(angle_deg)
        c, s = np.cos(angle), np.sin(angle)

        # Translate to rotation center
        shifted = pts - np.array([cx, cy])

        # Rotation matrix
        R = np.array([[c, -s],
                      [s,  c]])

        # Rotate and translate back
        return shifted @ R.T + np.array([cx, cy])
