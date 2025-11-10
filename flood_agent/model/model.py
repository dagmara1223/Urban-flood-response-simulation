import numpy as np
import matplotlib.pyplot as plt
from time import sleep
import rasterio
from rasterio.merge import merge
import glob
from rasterio.transform import rowcol, xy
import geopandas as gpd
import osmnx as ox
from rasterio.features import rasterize
from shapely.geometry import box
from pyproj import Transformer
from shapely.ops import transform as shp_transform

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

# , rain: float= 0.0 - usuniety argument
def flood_step(height: np.ndarray, water: np.ndarray, k : float, roads_mask)-> np.ndarray:
    # zmienne
    total_level = height + water # poziom całkowity
    new_water = water.copy() # kopia wody do zapisu zmian

    # integracja po wszystkich komorkach
    for i in range(1, height.shape[0] - 1):
        for j in range(1, height.shape[1] - 1):
            neighbors = total_level[i-1:i+2, j-1:j+2] # wycinek 3 na 3 sasiadow (8 kierunkow)

            diff = total_level[i, j] - neighbors # zmiany wzgledem aktualnej komorki

            # lokalny współczynnik przepływu: drogi ×2.0 - poniewaz droga przyspiesza szybkosc przeplywu
            local_k = np.where(roads_mask[i,j], k*2.0, k)
            flow = np.clip(diff * local_k, 0, None)

            total_outflow = flow.sum() - flow[1, 1] # calkowita ilosc wyplywajacej wody 

            # jesli cos wyplywa -> aktualizacja stanu wody
            if total_outflow > 0:
                new_water[i,j] -= total_outflow
                # przeplyw do sasiadow bez samej tej komorki
                new_water[i-1:i+2, j-1:j+2] += flow
                new_water[i, j] -= flow[1,1] 

    return np.clip(new_water, 0, None)

# polaczenie ze soba pobranych obszarow tiff
'''
tiffs = glob.glob("dem/*.tiff")
src_files_to_mosaic = []
for fp in tiffs:
    src = rasterio.open(fp)
    src_files_to_mosaic.append(src)

mosaic, out_transform = merge(src_files_to_mosaic)

out_meta = src.meta.copy()
out_meta.update({
    "driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_transform
})
'''
# zapis połączonego DEM
# with rasterio.open("krakow_merged.tif", "w", **out_meta) as dest:
#     dest.write(mosaic)


with rasterio.open("krakow_merged.tif") as src:
    height = src.read(1)
    transform = src.transform   # do późniejszego odczytu piksel_size
    pix_size_x = abs(transform[0])   # [m/pixel]
    pix_size_y = abs(transform[4]) 

    raster_crs = src.crs
   

#obszar rynku 
rynek = height[2000:3200, 3500:4800]
rynek = rynek[::6, ::6]

water = np.zeros_like(rynek, dtype=float)

# ------------------ area drog --------------------------------------------------------

r0, r1 = 1400, 2600
c0, c1 = 3800, 5000

# współrzędne geograficzne tego obszaru
x_min, y_max = xy(transform, r0, c0)
x_max, y_min = xy(transform, r1, c1)


# pobieramy bounding box w DEM CRS
bbox_poly = box(x_min, y_min, x_max, y_max)

from pyproj import CRS
raster_crs = CRS.from_epsg(2180)
# pobieramy drogi w WGS84
to_wgs84 = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True).transform
bbox_poly_wgs = shp_transform(to_wgs84, bbox_poly)

gdf_roads = ox.features_from_polygon(bbox_poly_wgs, {"highway": True})

# projekcja dróg do CRS DEM
roads = gdf_roads.to_crs(raster_crs)
roads["geometry"] = roads.buffer(5)

# rasteryzacja dróg na pełny DEM 
roads_raster_full = rasterize(
    [(geom, 1) for geom in roads.geometry],
    out_shape=height.shape,
    transform=transform,
    fill=0
)

# wycinek jak dla rynku - wazne - do zmiany gdy zmienia sie obszar height
roads_rynek = roads_raster_full[2000:3200, 3500:4800]

# downsampling taki jak przy glownym obszarze
roads_rynek = roads_rynek[::6, ::6]

# ------------------ koniec area drog ---------------------------------------------
roads_mask = roads_rynek.astype(bool)

# ------------------ area maski wisly ---------------------------------------------
# pobieram wisle
gdf_river = ox.features_from_polygon(bbox_poly_wgs, {"waterway": "river"})

# filtr tylko wisla - nie chcemy zalapania sie innej rzeki - Vistula
gdf_river = gdf_river[
    gdf_river.get("name", "").str.contains("Wis", case=False, na=False) |
    gdf_river.get("name", "").str.contains("Vist", case=False, na=False)
]

# jeśli pusta 
if gdf_river.empty:
    gdf_river = ox.features_from_polygon(bbox_poly_wgs, {"water": "river"})

# projekcja do CRS DEM
river = gdf_river.to_crs(raster_crs)

# bufor – bo linia rzeki ma szerokość
river["geometry"] = river.buffer(15)  # 15 m – można dać 20, 30 itd do zmian

river_raster_full = rasterize(
    [(geom, 1) for geom in river.geometry],
    out_shape=height.shape,
    transform=transform,
    fill=0
)

# wycinek rynku
river_rynek = river_raster_full[2000:3200, 3500:4800]
river_rynek = river_rynek[::6, ::6]

# maska wisły
river_mask = river_rynek.astype(bool)

# startowy poziom rzeki
water[river_mask] = 0.50  # 50 cm wody w korycie na starcie
# ----------------- koniec maski wisly ------------------------------------------

# dodajemy opady 
dt_seconds = 600.0  # co 10 min
dt_hours = dt_seconds / 3600.0

# funkcja mm/h -> metry slupa wody dodane w 1 iteracji 
def mmph_to_m_per_iteration(mm_per_hour: float)->float:
    return (mm_per_hour / 1000.0)*dt_hours # czyli mm->m i mnozymy przez czas kroku

# scenariusz odwzorowuje realne sumy opadów z powodzi 2010 w Krakowie mamy ≈141 mm
rain_block = [
    (6,6), # 6 h po 6mm/h - front pierwszy
    (12,3), # 12 h po 3 mm/h - dlugotrwaly deszcz
    (3,15), # 3h po 15 mm/h - najsilniejsze opady -> podtopienia
    (6,4) # 6h po 4 mm/h - schodzenie
]

rain_series = [] #seria intensywnosci per iteracja 
for hours, mmph in rain_block:
    steps = int(np.ceil(hours / dt_hours))
    rain_series.extend([mmph_to_m_per_iteration(mmph)] * steps)

total_mm = sum(h*mmph for h, mmph in rain_block)
print(f"Łączny opad scenariusza ≈ {total_mm} mm")

import os
output_folder = "data"
os.makedirs(output_folder, exist_ok=True)

k = 0.15 # startowo 
overflow_triggered = False  # sygnał czy już było przelanie
plt.figure(figsize=(10,6))
for t, rain_m in enumerate(rain_series):

    # deszcz
    water += rain_m

    # przepływ co X kroków
    if t % 5 == 0:
        water = flood_step(rynek, water, k=k, roads_mask=roads_mask)
    
    np.save(os.path.join(output_folder, f"water_step_{t:04d}.npy"), water)
    
    # sprawdzamy overflow wisly
    if (not overflow_triggered) and (water[river_mask].mean() > 1.5):
        print(f"*** UWAGA: Wisła PRZELAŁA WAŁY! (krok={t}, czas={t*10} minut) ***")
        
        # zwiększamy przepływ globalnie - wisla pcha szybciej wode
        k = 0.25
        
        # efekt gwałtownego wylania
        # water[rzeka sąsiadująca] += 0.4 m
    
        # piksele sąsiadujące z river_mask
        from scipy.ndimage import binary_dilation
        ring = binary_dilation(river_mask) & (~river_mask)
        water[ring] += 0.4  # 40 cm nagle w okolicy wałów
        
        overflow_triggered = True

    # animacja co 20 kroków
    if t % 20 == 0:
        plt.clf()

        plt.imshow(roads_rynek, cmap="binary", alpha=0.18, origin="upper")
        plt.contour(roads_rynek, levels=[0.5], colors='black', linewidths=0.5)

        # terrain
        im1 = plt.imshow(rynek, cmap='terrain', origin='upper')

        # water overlay
        im2 = plt.imshow(water, cmap='Blues', alpha=0.65, origin='upper')

        # legenda 1 (wysokość terenu)
        cbar1 = plt.colorbar(im1, fraction=0.046, pad=0.04)
        cbar1.set_label("Wysokość terenu [m n.p.m.]")

        # legenda 2 (głębokość wody)
        cbar2 = plt.colorbar(im2, fraction=0.046, pad=0.12)
        cbar2.set_label("Głębokość wody [m]")

        plt.title(f"Deszcz + spływ powierzchniowy — krok {t}")
        plt.pause(0.5)
plt.tight_layout()
plt.show()



