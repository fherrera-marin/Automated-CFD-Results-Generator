# scripts/plot_airfoil.py

from geometry.naca4 import NACA4Airfoil
from geometry.plot import AirfoilPlotter

def main():
    airfoil = NACA4Airfoil.from_code("2512")
    contour = airfoil.coordinates(step=0.01)
    AirfoilPlotter.plot_contour(contour, title="NACA")
    airfoil.plot_sdf()



if __name__ == "__main__":
    main()
