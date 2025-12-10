from datetime import datetime
import os
import networkx as nx
from evac_model import EvacModel, animate_simulation, save_stats_to_csv
from flood_agent.model.model import FloodModel
import matplotlib.pyplot as plt
import numpy as np


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

    run_flood_simulation = True
    run_evacuation_simulation = True

    # Flood simulation parameters ------------------------------------------------------------
    k = 0.15 # startowo 
    dem_path = "Data/krakow_merged.tif"
    # rynek
    area_bounds=(0, 4838, 0, 11138)
    #area_bounds = (2000, 3200, 3500, 4800)
    # scenariusz odwzorowuje realne sumy opadów z powodzi 2010 w Krakowie mamy ≈141 mm
    rain_block = [
        (6,6), # 6 h po 6mm/h - front pierwszy
        (12,3), # 12 h po 3 mm/h - dlugotrwaly deszcz
        (3,15), # 3h po 15 mm/h - najsilniejsze opady -> podtopienia
        (6,4) # 6h po 4 mm/h - schodzenie
    ]
    #-------------------------------------------------------------------------------------------

    # Evacuation simulation parameters -------------------------------------------------------
    graph_path = 'Data/krakow_roads_all_2.graphml'
    dem_path = 'Data/krakow_merged.tif'
    n_agents = 100 # 8000
    G = build_example_graph(graph_path)
    #-------------------------------------------------------------------------------------------

    # Run evacuation simulation ---------------------------------------------------------------
    if run_evacuation_simulation:
        # create output folder with timestamp
        curr_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        folder_path = f"output/run_{curr_time}"
        os.makedirs(folder_path, exist_ok=True)

        flood_model = None
        if run_flood_simulation:
            flood_model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)
        model = EvacModel(n_agents=n_agents, roads_graph=G, dem_path=dem_path, flood_model=flood_model)
        
        for t in range(1600):
            print(f"Step {t}")
            model.step()
            if t % 80 == 0:
                model.create_agents(200)
        
        # Create animation
        save_stats_to_csv(model, folder_path)
        anim = animate_simulation(model, save_path=os.path.join(folder_path, "evacuation_simulation.mp4"), fps=5)

    # Run flood simulation (only if no evacuation) -------------------------------------------
    if run_flood_simulation and not run_evacuation_simulation:
        
        model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)

        plt.figure(figsize=(10,6))
        for t in range(len(model.rain_series)):
            model.step(t)

            if t % 10 == 0:

                fig, ax = plt.subplots(figsize=(12,6))

                # dem
                ax.imshow(model.area, cmap='terrain',
                        vmin=model.global_min,
                        vmax=model.global_max)

                # maska wody
                vis_water = model.water.copy()
                vis_water[model.roads_mask] = 0
                water_mask = np.where(vis_water > 0.1, vis_water, np.nan)

                ax.imshow(
                    water_mask,
                    cmap='Blues',
                    alpha=0.7,
                    vmin=0,
                    vmax=1.0
                )
                ax.imshow(model.river_mask, cmap="Blues", alpha=0.3)

                # kontury woda glebsza 
                try:
                    contours = ax.contour(
                        model.water,
                        levels=[0.05,0.10,0.20,0.40,0.60],
                        colors='blue',
                        linewidths=0.6
                    )
                    ax.clabel(contours, inline=True, fontsize=6, fmt="%.2f m")
                except:
                    pass

                ax.set_title(f"Krok {t} – Kraków (zalanie >2 cm)")
                ax.axis("off")

                outfile = f"frames/frame_{t:04d}.png"
                fig.savefig(outfile, dpi=150, bbox_inches='tight')
                plt.close(fig)

                print("Zapisano:", outfile)



        
        

