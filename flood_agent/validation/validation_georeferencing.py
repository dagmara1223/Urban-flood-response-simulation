import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS


DEM_PATH = "Data/krakow_merged.tif"
PNG_PATH = "Data/flood_map.png"
OUTPUT_PATH = "Data/validation_krakow.tif"

with rasterio.open(DEM_PATH) as dem:
    bounds = dem.bounds
    crs = dem.crs

x_min = bounds.left
y_max = bounds.top
x_max = bounds.right
y_min = bounds.bottom

print("Using DEM bounds:")
print("x_min:", x_min)
print("y_max:", y_max)
print("x_max:", x_max)
print("y_min:", y_min)
print("CRS:", crs)


img = Image.open(PNG_PATH).convert("L")  # grayscale; use "RGB" if needed

img_arr = np.array(img)
if img_arr.ndim == 3:
    height, width, _ = img_arr.shape
else:
    height, width = img_arr.shape

print("PNG loaded:", PNG_PATH)
print("PNG size:", width, "x", height)

transform = from_bounds(x_min, y_min, x_max, y_max, width, height)

with rasterio.open(
    OUTPUT_PATH,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=1,
    dtype=img_arr.dtype,
    crs=crs,
    transform=transform
) as dst:
    dst.write(img_arr, 1)

print("Georeferenced PNG saved as:", OUTPUT_PATH)

import matplotlib.pyplot as plt

dem = rasterio.open("Data/krakow_merged.tif")
flood = rasterio.open("Data/validation_krakow.tif")

dem_img = dem.read(1)
flood_img = flood.read(1)

plt.figure(figsize=(40,40))
plt.imshow(dem_img, cmap="terrain")
plt.imshow(flood_img, cmap="Reds", alpha=0.3)
plt.title("DEM + Flood Map Overlay")
plt.savefig("Data/check.png")