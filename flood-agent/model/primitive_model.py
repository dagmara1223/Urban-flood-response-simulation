import numpy as np
import matplotlib.pyplot as plt
from time import sleep

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
                new_water[i,j] -= total_outflow #komorka traci wode
                new_water[i-1:i+2, j-1:j+2] += flow # sasiad otrzymuje wode

    # dodanie opasu 
    if rain > 0:
        new_water += rain 

    new_water = np.clip(new_water, 0, None) 

    return new_water


n = 5
height = np.array([
    [2,1,1,1,1],
    [2,1,1,1,1],
    [2,2,1,1,1],
    [2,2,1,1,1],
    [2,2,2,1,1]
])
water = np.zeros((n, n))
water[0, 0] = 1.0

for t in range(15):
    water = flood_step(height, water, k=0.15)
    plt.imshow(water, cmap='Blues', vmin=0, vmax=1)
    plt.title(f"Krok {t}")
    plt.pause(0.3)
plt.show()
