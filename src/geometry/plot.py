# plot.py
import numpy as np
import matplotlib.pyplot as plt


class AirfoilPlotter:
    """Plot utilities for 2D airfoil point sets (Nx2 arrays)."""

    @staticmethod
    def plot_contour(contour: np.ndarray, title: str = "Airfoil", show_points: bool = True):
        """
        Plot a 2D airfoil contour.

        Parameters
        ----------
        contour : np.ndarray
            Nx2 array of [x, y] points.
        title : str
            Plot title.
        show_points : bool
            If True, shows point markers.
        """
        pts = np.asarray(contour, dtype=float)

        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError("contour must be an Nx2 array")

        x = pts[:, 0]
        y = pts[:, 1]

        plt.figure()
        if show_points:
            plt.plot(x, y, "-o", markersize=2)
        else:
            plt.plot(x, y, "-")

        plt.axis("equal")
        plt.grid(True)
        plt.title(title)
        plt.xlabel("x")
        plt.ylabel("y")

        plt.show()
        plt.pause(0.001)

    @staticmethod
    def plot_upper_lower(
        upper: np.ndarray,
        lower: np.ndarray,
        title: str = "Airfoil (upper/lower)",
        show_points: bool = True
    ):
        """
        Plot upper and lower surfaces separately.

        Parameters
        ----------
        upper : np.ndarray
            Nx2 points for upper surface.
        lower : np.ndarray
            Nx2 points for lower surface.
        title : str
            Plot title.
        show_points : bool
            If True, shows point markers.
        """
        up = np.asarray(upper, dtype=float)
        lo = np.asarray(lower, dtype=float)

        if up.ndim != 2 or up.shape[1] != 2:
            raise ValueError("upper must be an Nx2 array")
        if lo.ndim != 2 or lo.shape[1] != 2:
            raise ValueError("lower must be an Nx2 array")

        plt.figure()
        if show_points:
            plt.plot(up[:, 0], up[:, 1], "-o", markersize=2, label="Upper")
            plt.plot(lo[:, 0], lo[:, 1], "-o", markersize=2, label="Lower")
        else:
            plt.plot(up[:, 0], up[:, 1], "-", label="Upper")
            plt.plot(lo[:, 0], lo[:, 1], "-", label="Lower")

        plt.axis("equal")
        plt.grid(True)
        plt.title(title)
        plt.xlabel("x")
        plt.ylabel("y")
        plt.legend()
        
        plt.show()
        plt.pause(0.001)
