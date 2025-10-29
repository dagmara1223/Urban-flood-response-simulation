import osmnx as ox
import networkx as nx

'''
# Define the place name and network type
place_name = "Kraków, Poland"
network_type = "drive"  # Options: 'walk', 'bike', 'drive'

# Download the road network
G_osm = ox.graph_from_place(place_name, network_type=network_type)
'''
# 200 meters around the center point
center = (50.04340584275002, 19.947057402111867)
distance = 1000

# Driving network
G_drive = ox.graph_from_point(center, dist=distance, network_type='drive')
G_drive = ox.project_graph(G_drive)

# Walking network
G_walk = ox.graph_from_point(center, dist=distance, network_type='walk')
G_walk = ox.project_graph(G_walk)

G = nx.Graph()

# Add driving edges
for u, v, data in G_drive.edges(data=True):
    length = data.get('length', 1.0)
    G.add_edge(u, v, length=length, safe='yes')


# Add node positions
for n, data in G_drive.nodes(data=True):
    G.nodes[n]['pos'] = (data['x'], data['y'])

# Keep only the largest connected component of the combined graph
largest_cc = max(nx.connected_components(G), key=len)
G = G.subgraph(largest_cc).copy()


# Convert position attributes to separate x and y attributes
for n, data in G.nodes(data=True):
    x, y = data['pos']
    data['x'] = float(x)
    data['y'] = float(y)
    del data['pos']  # remove the tuple

print(f"\nNumber of nodes: {len(G.nodes)}")
print(f"Number of edges: {len(G.edges)}")

print("Sample nodes with positions:")
for n, data in list(G.nodes(data=True))[:5]:
    print(n, data)
print("\nSample edges with length:")
for u, v, data in list(G.edges(data=True))[:5]:
    print(u, v, data)

# Save the graph to a file for later use
nx.write_graphml(G, "Data/krakow_roads.graphml")
print("Graph saved to Data/krakow_roads.graphml")