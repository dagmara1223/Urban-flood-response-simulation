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

rescue_points = {
    "JRG1": (4440, 1330),
    "JRG2": (3990, 4070),
    "JRG4": (10540, 140),
    "JRG5": (5800, 4780),
    "JRG6": (11090, 3260),

    "Ambulance_Base": (5110, 1330),
    "Ambulance_Mateczne": (4330, 3940),
    "Ambulance_Prokocim": (7200, 4770),
}


safe_points = {
    'ZoneA_1': (3174.4, 4299.4),
    'ZoneA_2': (2978.3, 4539.4),
    'ZoneA_3': (2686.4, 4868.2),
    'ZoneA_4': (3037.9, 4091.7),
    'ZoneA_5': (3153.6, 4592.7),
    'ZoneA_6': (2986.7, 4809.2),
    
    'ZoneB_1': (6990.7, 4994.7),
    'ZoneB_2': (8446.5, 4742.1),
    'ZoneB_3': (10604.6, 4644.8),
    'ZoneB_4': (10055.1, 4307.5),
    'ZoneB_5': (7979.1, 4567.0),
    'ZoneB_6': (8703.3, 4879.1),
    'ZoneB_7': (9035.3, 4344.2),
    'ZoneB_8': (10841.6, 4071.6),
    'ZoneB_9': (6451.0, 4317.0),
    'ZoneB_10': (6389.3, 4935.6),
    
    'ZoneC_1': (2119.6, 102.6),
    'ZoneC_2': (6615.0, 483.8),
    'ZoneC_3': (874.8, 748.3),
    'ZoneC_4': (311.1, 934.8),
    'ZoneC_5': (4398.3, 204.2),
    'ZoneC_6': (1511.1, 978.5),
    'ZoneC_7': (1773.2, 11.0),
    'ZoneC_8': (10947.0, 450.6),
    'ZoneC_9': (6206.4, 539.2),
    'ZoneC_10': (10115.6, 323.3),
    'ZoneC_11': (10900.6, 972.3),
    'ZoneC_12': (5362.7, 424.6),
    'ZoneC_13': (2472.7, 304.7),
    'ZoneC_14': (2418.5, 9.6),
    'ZoneC_15': (6847.7, 756.7)
}


def nearest_node(G, x, y):
    return min(G.nodes, key=lambda n: (G.nodes[n]['pos_array_x'] - x)**2 + (G.nodes[n]['pos_array_y'] - y)**2)


# -------------------------------
# Ścieżki i DEM
# -------------------------------
dem_path = "Data/krakow_merged.tif"
output_graph_path = "Data/krakow_roads_all_2.graphml"

with rasterio.open(dem_path) as src:
    height_full = src.read(1)
    transform = src.transform
    raster_crs = src.crs

r0, r1 = 0, 4838
c0, c1 = 0, 11138
height = height_full[r0:r1, c0:c1]

nrows, ncols = height.shape
water_map = np.zeros_like(height, dtype=float)

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
G_walk = ox.graph_from_bbox(bbox_poly_wgs.bounds, network_type='walk', simplify=True)
G_walk = ox.project_graph(G_walk, to_crs=raster_crs_proj)

allowed = {"residential", "primary", "secondary", "tertiary", "service"}

edges_to_remove = []

for u, v, k, data in G_walk.edges(keys=True, data=True):
    hw = data.get("highway")

    if isinstance(hw, list):
        ok = any(h in allowed for h in hw)
    else:
        ok = hw in allowed

    if not ok:
        edges_to_remove.append((u, v, k))

G_walk.remove_edges_from(edges_to_remove)
isolated = list(nx.isolates(G_walk))
G_walk.remove_nodes_from(isolated)

for n, data in G_drive.nodes(data=True):
    data['x'] = float(data['x'])
    data['y'] = float(data['y'])

for n, data in G_walk.nodes(data=True):
    data['x'] = float(data['x'])
    data['y'] = float(data['y'])

G = nx.Graph()
for u, v, d in G.edges(data=True):
    d['road_type'] = 'unknown'

for u, v, data in G_drive.edges(data=True):
    length = data.get('length', 1.0)
    G.add_edge(u, v, length=length, road_type="drive")
for n, data in G_drive.nodes(data=True):
    G.add_node(n, x=data['x'], y=data['y'])

for u, v, data in G_walk.edges(data=True):
    length = data.get('length', 1.0)
    if G.has_edge(u, v):
        G[u][v]["road_type"] = "both"
    else:
        G.add_edge(u, v, length=length, road_type="walk")
for n, data in G_walk.nodes(data=True):
    G.add_node(n, x=data['x'], y=data['y'])

# -------------------------------
# Funkcja map_depth_to_graph
# -------------------------------
def map_depth_to_graph(G, water_map, roads_raster, transform):
    nrows, ncols = water_map.shape

    pos_array = np.full((nrows, ncols), -1, dtype=int)

    for n, data in G.nodes(data=True):
        x, y = data['x'], data['y']
        row, col = rowcol(transform, x, y)
        row = max(0, min(row, nrows - 1))
        col = max(0, min(col, ncols - 1))

        data['depth'] = float(0)

        data['pos_array_y'] = int(row)
        data['pos_array_x'] = int(col)

        pos_array[row, col] = n

    for u, v, d in G.edges(data=True):
        d['safe'] = 'yes'

    return pos_array

# -------------------------------
# 5 Wywołanie funkcji i zapis
# -------------------------------
pos_array = map_depth_to_graph(G, water_map, roads_raster_full, transform)

rescue_nodes = {}
for name, (rx, ry) in rescue_points.items():
    node = nearest_node(G, rx, ry)
    G.nodes[node]["is_rescue_base"] = True
for name, (sx, sy) in safe_points.items():
    node = nearest_node(G, sx, sy)
    G.nodes[node]["is_safe_spot"] = True

G_undirected = nx.Graph(G)
largest_cc_nodes = max(nx.connected_components(G_undirected), key=len)
G= G.subgraph(largest_cc_nodes).copy()

nx.write_graphml(G, output_graph_path)
print(f"Graph saved to {output_graph_path}")