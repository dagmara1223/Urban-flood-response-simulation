import os
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import box
from shapely.ops import transform as shp_transform
from pyproj import CRS, Transformer
import osmnx as ox
import networkx as nx
from rasterio.transform import rowcol
from rasterio.transform import Affine

# -------------------------------
# Ścieżki i DEM
# -------------------------------
dem_path = "krakow_merged.tif"
output_graph_path = "Data/krakow_roads2.graphml"

with rasterio.open(dem_path) as src:
    height_full = src.read(1)
    transform = src.transform
    raster_crs = src.crs

'''
To się zmienia:
'''
r0, r1 = 2000, 3200
c0, c1 = 3500, 4800

height = height_full[r0:r1, c0:c1]
height = height[::6, ::6]

nrows, ncols = height.shape
water_map = np.zeros_like(height, dtype=float)

transform = transform * Affine.translation(c0, r0) * Affine.scale(6, 6)

'''
^^^^^^
'''

x_min, y_max = rasterio.transform.xy(transform, 0, 0)
x_max, y_min = rasterio.transform.xy(transform, nrows-1, ncols-1)
bbox_poly = box(x_min, y_min, x_max, y_max)


# -------------------------------
# Pobranie dróg z OSM
# -------------------------------
raster_crs_proj = CRS.from_epsg(2180)
to_wgs84 = Transformer.from_crs(raster_crs_proj, "EPSG:4326", always_xy=True).transform
bbox_poly_wgs = shp_transform(to_wgs84, bbox_poly)

gdf_roads = ox.features_from_polygon(bbox_poly_wgs, {"highway": True})
roads = gdf_roads.to_crs(raster_crs_proj)
roads["geometry"] = roads.buffer(5)

roads_raster_full = rasterize(
    [(geom, 1) for geom in roads.geometry],
    out_shape=(nrows, ncols),
    transform=transform,
    fill=0
)

# -------------------------------
# Pobranie grafu OSM
# -------------------------------
left, bottom, right, top = bbox_poly_wgs.bounds
G_drive = ox.graph_from_bbox(bbox_poly_wgs.bounds, network_type='drive')
G_drive = ox.project_graph(G_drive, to_crs=raster_crs_proj)
G_walk = ox.graph_from_bbox(bbox_poly_wgs.bounds, network_type='walk')
G_walk = ox.project_graph(G_walk, to_crs=raster_crs_proj)

# Dodanie pozycji x,y w CRS DEM
for n, data in G_drive.nodes(data=True):
    data['x'] = float(data['x'])
    data['y'] = float(data['y'])
for n, data in G_walk.nodes(data=True):
    data['x'] = float(data['x'])
    data['y'] = float(data['y'])

G = nx.Graph()
for u, v, data in G_drive.edges(data=True):
    length = data.get('length', 1.0)
    G.add_edge(u, v, length=length, safe='yes')
for n, data in G_drive.nodes(data=True):
    G.add_node(n, x=data['x'], y=data['y'])

for u, v, data in G_walk.edges(data=True):
    length = data.get('length', 1.0)
    G.add_edge(u, v, length=length, safe='yes')
for n, data in G_walk.nodes(data=True):
    G.add_node(n, x=data['x'], y=data['y'])

# -------------------------------
# Funkcja map_depth_to_graph
# -------------------------------
def map_depth_to_graph(G, water_map, roads_raster, transform):
    nrows, ncols = water_map.shape

    # pos_array: współrzędne węzłów w indeksach macierzy water_map
    pos_array = np.full((nrows, ncols), -1, dtype=int)

    for n, data in G.nodes(data=True):
        x, y = data['x'], data['y']
        row, col = rowcol(transform, x, y)
        row = max(0, min(row, nrows - 1))
        col = max(0, min(col, ncols - 1))

        data['depth'] = float(0)
        data['on_road'] = bool(roads_raster[row, col])

        # zapis pozycji w macierzy do węzła
        data['pos_array_y'] = int(row)
        data['pos_array_x'] = int(col)

        pos_array[row, col] = n  # węzeł w danej komórce water_map

    # Oznaczenie krawędzi
    for u, v, d in G.edges(data=True):
        d['safe'] = 'yes'

    return pos_array

# -------------------------------
# 5Wywołanie funkcji i zapis
# -------------------------------
pos_array = map_depth_to_graph(G, water_map, roads_raster_full, transform)

nx.write_graphml(G, output_graph_path)
print(f"Graph saved to {output_graph_path}")



# -------------------------------
# 6Wizualizacja DEM + drogi + węzły grafu - SPRAWDZENIE POPRAWNOŚĆI
# -------------------------------
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 10))
im1 = plt.imshow(height, cmap='terrain', origin='upper')
plt.imshow(water_map, cmap='Blues', alpha=0.5, origin='upper')
cbar1 = plt.colorbar(im1, fraction=0.046, pad=0.04)
cbar1.set_label("Wysokość terenu [m n.p.m.]")

# Rysowanie dróg rasteryzowanych
plt.imshow(roads_raster_full, cmap='Greys', alpha=0.3, origin='upper')


x = nx.get_node_attributes(G, "pos_array_x")  
y = nx.get_node_attributes(G, "pos_array_y")  

# Rysowanie węzłów grafu
node_x = [data['pos_array_x'] for n, data in G.nodes(data=True)]
node_y = [data['pos_array_y'] for n, data in G.nodes(data=True)]
plt.scatter(node_x, node_y, c='red', s=10, label='Graph nodes')

# Rysowanie krawędzi
for u, v in G.edges():
    x_vals = [G.nodes[u]['pos_array_x'], G.nodes[v]['pos_array_x']]
    y_vals = [G.nodes[u]['pos_array_y'], G.nodes[v]['pos_array_y']]
    plt.plot(x_vals, y_vals, color='black', linewidth=1, alpha=0.7)

plt.legend()
plt.title("DEM + Flood Map + Graph Nodes + Roads")
plt.xlabel("X [pixels/meters]")
plt.ylabel("Y [pixels/meters]")
plt.show()
