import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from mpl_toolkits.mplot3d import Axes3D
import rasterio
import contextily as ctx
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask

"""
Uproszczony model przepływu powierzchniowego.
Dla każdej komórki siatki obliczamy różnicę poziomów wody - wysokość terenu + aktualna wysokość
słupa wody względem sąsiadów. Nadmiar wody spływa do niżej osadzonych komórek.

Paramtery: 
height: np.array      - Dwuwymiarowa macierz (N x M) opisująca wysokość terenu w metrach.
water: np.array       - Macierz o tych samych wymiarach zwracająca poziom słupa wody.
k : float             - Określa, jaka część różnicy wysokości jest przenoszona do sąsiadów
                        w jednym kroku czasowym.

Zwraca:
np.ndarray            - Zaktualizowana macierz `water` po jednym kroku czasowym symulacji

Zasada przeplywu:
 1. Całkowity poziom wody w komórce:
       z(i,j) = height(i,j) + water(i,j)
2. Różnica względem sąsiadów (8-kierunkowych):
       Δz = z(i,j) - z(m,n)
3. Przepływ możliwy tylko tam, gdzie Δz > 0.
       Q(i,j→m,n) = k * max(0, Δz)
4. Suma odpływów z komórki = suma dopływów do sąsiadów
"""

def flood_step(height: np.ndarray, water: np.ndarray, k : float = 0.1, rain: float= 0.0)-> np.ndarray:
    # zmienne
    total_level = height + water # poziom całkowity
    new_water = water.copy() # kopia wody do zapisu zmian

    # integracja po wszystkich komorkach
    for i in range(1, height.shape[0] - 1):
        for j in range(1, height.shape[1] - 1):
            neighbors = total_level[i-1:i+2, j-1:j+2] # wycinek 3 na 3 sasiadow (8 kierunkow)

            diff = total_level[i, j] - neighbors # zmiany wzgledem aktualnej komorki

            flow = np.clip(diff * k, 0, None) # przeplyw tam, gdzie sasiad jest nizszy(diff>0)

            total_outflow = flow.sum() - flow[1, 1] # calkowita ilosc wyplywajacej wody 

            # jesli cos wyplywa -> aktualizacja stanu wody
            if total_outflow > 0:
                new_water[i,j] -= total_outflow
                # przeplyw do sasiadow bez samej tej komorki
                for di in range(-1, 2):
                    for dj in range(-1, 2):
                        if di == 0 and dj == 0:
                            continue  # pomijanie środka
                        new_water[i+di, j+dj] += flow[di+1, dj+1]

    # dodanie opasu 
    if rain > 0:
        new_water += rain 

    new_water = np.clip(new_water, 0, None) 

    return new_water

<<<<<<< HEAD:flood_agent/model/primitive_model.py
'''
with rasterio.open('StandardResolution.tiff') as src:
=======

with rasterio.open('HighResolution.tiff') as src:
>>>>>>> 7eed55f (Update primitive_model.py):flood-agent/model/primitive_model.py
    height = src.read(1).astype(float)
    height[height == src.nodata] = np.nan
    height = np.nan_to_num(height, nan=np.nanmin(height))

height = height[600:1100, 600:1100] 

water = np.zeros_like(height)
water[50:55, 90:95] = 50.0

for t in range(20):
    water = flood_step(height, water, k=0.12)
    if t % 5 == 0:
        plt.clf()  
        plt.imshow(height, cmap='terrain', origin='upper')
        plt.imshow(water, cmap='Blues', alpha=0.6, origin='upper', vmin=0, vmax=12)
        plt.title(f"Rozlew wody na terenie – krok {t}")
        plt.colorbar(label="Głębokość wody [m]")
        plt.pause(0.3)
plt.show()
<<<<<<< HEAD:flood_agent/model/primitive_model.py

plt.imshow(height, cmap='terrain', origin='upper')
plt.imshow(water, cmap='Blues', alpha=0.6, origin='upper', vmin=0, vmax=np.max(water)/3)
plt.title(f"Rozlew wody na terenie – krok {t}")
plt.colorbar(label="Głębokość wody [m]")
plt.show()

# X, Y = np.meshgrid(np.arange(water.shape[0]), np.arange(water.shape[1]))
# fig = plt.figure(figsize=(7,5))
# ax = fig.add_subplot(111, projection='3d')
# ax.plot_surface(X, Y, height + water, cmap='terrain')
# ax.set_title("Powierzchnia terenu + woda")
# plt.show()

'''
=======
>>>>>>> 7eed55f (Update primitive_model.py):flood-agent/model/primitive_model.py
