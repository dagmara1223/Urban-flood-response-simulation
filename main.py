from datetime import datetime
import os
import networkx as nx
from agent_model.evac_model import EvacModel, animate_simulation, save_stats_to_csv
from flood_agent.model import FloodModel
import matplotlib.pyplot as plt
import rasterio
import numpy as np
from run_analysis import stats_summary
def build_example_graph(path):
    # Tworzenie grafu drogowego
    G = nx.read_graphml(path)
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']/4), float(data['y']/4))
        data['pos_array'] = (int(data['pos_array_x']/4), int(data['pos_array_y']/4))
    G.remove_edges_from(nx.selfloop_edges(G))
    return G


if __name__ == "__main__":
    # Flood simulation parameters ------------------------------------------------------------
    k = 0.15 # startowo 
    dem_path = "Data/krakow_merged.tif"
    area_bounds=(0, 4838, 0, 11138)
    rain_block = [
        (6,6), # 6 h po 6mm/h - front pierwszy
        (12,3), # 12 h po 3 mm/h - dlugotrwaly deszcz
        (3,15), # 3h po 15 mm/h - najsilniejsze opady -> podtopienia
        (6,4) # 6h po 4 mm/h - schodzenie
    ]
    #-------------------------------------------------------------------------------------------

    # Evacuation simulation parameters -------------------------------------------------------
    graph_path = 'Data/krakow_roads_all_2.graphml'
    n_agents = 100
    n_rescue = 6
    G = build_example_graph(graph_path)
    #-------------------------------------------------------------------------------------------

    
    curr_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    folder_path = f"output/run_{curr_time}"
    os.makedirs(folder_path, exist_ok=True)

    flood_model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)
    model = EvacModel(n_agents=n_agents, roads_graph=G, dem_path=dem_path, flood_model=flood_model, n_rescue=n_rescue)
    
    for t in range(2):
        print(f"Step {t}")
        model.step()                
    
    save_stats_to_csv(model, folder_path)
    animate_simulation(model, save_path=os.path.join(folder_path, "evacuation_simulation.mp4"), fps=5)
    
    stats_summary(folder_path, "standard")