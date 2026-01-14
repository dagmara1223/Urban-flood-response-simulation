from datetime import datetime
import os
import networkx as nx
import sys

from agent_model.citizen_agent import CitizenDecisionMakingMode
from agent_model.evac_model import EvacModel, save_stats_to_csv, animate_simulation_live
from flood_agent.model import FloodModel
from run_analysis import stats_summary

def build_example_graph(path):
    G = nx.read_graphml(path)
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']/4), float(data['y']/4))
        data['pos_array'] = (int(data['pos_array_x']/4), int(data['pos_array_y']/4))
    G.remove_edges_from(nx.selfloop_edges(G))
    return G


if __name__ == "__main__":

    scenario = 0 # default
    steps = 2
    if len(sys.argv) > 1:
        scenario = int(sys.argv[1])
        print(f"Scenario {sys.argv[1]}")
        if scenario not in [0,1,2,3,4,5,6]: # 0: default, 1: 2 x recue, 2: 3 x rescue, 3: 2 x rain, 4: decision making 1, 5: decision making 2, 6: decision making 3
            scenario = 0
        if len(sys.argv) > 2:
            steps = int(sys.argv[2])
            print(f"Steps {sys.argv[2]}")

        
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
    decision_making_mode = None
    G = build_example_graph(graph_path)
    #-------------------------------------------------------------------------------------------

    # Scenario adjustments -------------------------------------------------------------------
    if scenario == 1:
        n_rescue = n_rescue * 2
    elif scenario == 2:
        n_rescue = n_rescue * 3
    elif scenario == 3:
        rain_block = [ (6,12), (12,6), (3,30), (6,8) ]
    elif scenario == 4:
        decision_making_mode = [CitizenDecisionMakingMode.RANDOM, CitizenDecisionMakingMode.FOLLOWER, CitizenDecisionMakingMode.DIJIKSTRA, 
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA,
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA]
    elif scenario == 5:
        decision_making_mode = [CitizenDecisionMakingMode.RANDOM, CitizenDecisionMakingMode.RANDOM, CitizenDecisionMakingMode.DIJIKSTRA, 
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA,
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA]
    elif scenario == 6:
        decision_making_mode = [CitizenDecisionMakingMode.FOLLOWER, CitizenDecisionMakingMode.FOLLOWER, CitizenDecisionMakingMode.DIJIKSTRA, 
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA,
                                CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA]
    #-------------------------------------------------------------------------------------------

    curr_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    folder_path = f"output/run_{curr_time}"
    os.makedirs(folder_path, exist_ok=True)

    flood_model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)
    model = EvacModel(n_agents=n_agents, roads_graph=G, dem_path=dem_path, flood_model=flood_model, n_rescue=n_rescue, decision_making_mode=decision_making_mode)
    
    for t in range(steps):
        print(f"Step {t}")
        model.step()                
    
    save_stats_to_csv(model, folder_path)
    animate_simulation_live(model, fps=5)

    stats_summary(folder_path, f"scenario {scenario}", flood_model.rain_series)