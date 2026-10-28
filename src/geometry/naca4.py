import numpy as np
import cadquery as cq
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt

class NACA4Airfoil:
    def __init__(self, M_digit, P_digit, T_digits,
                 closed_te=True, name=None):

        self.M_digit = M_digit
        self.P_digit = P_digit
        self.T_digits = T_digits
        self.closed_te = closed_te

        self.M = M_digit / 100
        self.P = P_digit / 10
        self.T = T_digits / 100

        self.name=name 

        self.__validate()

    @classmethod
    def from_code(cls, code: str, closed_te=True, orientation_deg=0.0):
        if len(code) != 4 or not code.isdigit():
            raise ValueError("Invalid NACA 4-digit code.")
        return cls(int(code[0]), int(code[1]), int(code[2:]),closed_te=closed_te, name=f"NACA {code}")

    # ==========================
    # PRIVATE INTERNAL METHODS
    # ==========================

    def __validate(self):
        errors = []
        if not (0.0 <= self.M <= 0.09):
            errors.append(f"M={self.M_digit} must be between 0 and 9.")
        if self.M > 0 and not (0.1 <= self.P <= 0.9):
            errors.append(f"P={self.P_digit} must be between 1 and 9 if M > 0.")
        if not (0.01 <= self.T <= 0.40):
            errors.append(f"T={self.T_digits} must be between 01 and 40.")
        if errors:
            raise ValueError("\n".join(errors))
            
    # ==========================
    # PUBLIC INTERFACE
    # ==========================


    def coordinates(self, step):
        x = np.arange(0.0, 1.0 + step / 2, step)

        a0, a1, a2, a3 = 0.2969, -0.1260, -0.3516, 0.2843
        a4 = -0.1036 if self.closed_te else -0.1015

        yt = (self.T / 0.2) * (
            a0*np.sqrt(x) + a1*x + a2*x**2 + a3*x**3 + a4*x**4
        )

        yc = np.zeros_like(x)
        dyc_dx = np.zeros_like(x)

        if self.P <= 0 or self.P >= 1 or self.M == 0:
            yc[:] = 0.0
            dyc_dx[:] = 0.0
        else:
            front = x < self.P
            back = ~front

            yc[front] = (self.M / self.P**2) * (2*self.P*x[front] - x[front]**2)
            dyc_dx[front] = (2*self.M / self.P**2) * (self.P - x[front])

            yc[back] = (self.M / (1-self.P)**2) * (
                1 - 2*self.P + 2*self.P*x[back] - x[back]**2
            )
            dyc_dx[back] = (2*self.M / (1-self.P)**2) * (self.P - x[back])

        theta = np.arctan(dyc_dx)

        xu = x - yt*np.sin(theta)
        yu = yc + yt*np.cos(theta)
        xl = x + yt*np.sin(theta)
        yl = yc - yt*np.cos(theta)

        upper = np.column_stack([xu, yu])
        lower = np.column_stack([xl, yl])
        contour = np.vstack([upper[::-1], lower[1:]])

        return contour
    
    def compute_sdf(
        self,
        *,
        airfoil_step: float = 0.002,
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
        contour = self.coordinates(airfoil_step)
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
    
    def plot_sdf(self):

        sdf = self.compute_sdf()
        plt.imshow(sdf, cmap='viridis') 
        plt.colorbar()  
        if self.name is not None:
            plt.title(f"SDF – {self.name}")
        else:
            plt.title("SDF – NACA 4-digit airfoil")
        plt.xlabel("x")
        plt.ylabel("y")
        plt.axis("equal")
        plt.show()
        