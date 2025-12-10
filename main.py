from datetime import datetime
import os
import networkx as nx
from evac_model import Model
from flood_agent.model.model import FloodModel
import matplotlib.pyplot as plt
from flood_agent.validation.validation import validate_model_flood
import rasterio

def build_example_graph(path):
    # Tworzenie grafu drogowego
    G = nx.read_graphml(path)
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']), float(data['y']))
        data['pos_array'] = (int(data['pos_array_x']), int(data['pos_array_y']))
    G.remove_edges_from(nx.selfloop_edges(G))
    return G


if __name__ == "__main__":

    run_flood_simulation = True
    run_evacuation_simulation = False
    run_validation = True

    # Flood simulation parameters ------------------------------------------------------------
    k = 0.15 # startowo 
    dem_path = "Data/krakow_merged.tif"
    # rynek
    area_bounds=(2000, 3200, 3500, 4800)
    # scenariusz odwzorowuje realne sumy opadów z powodzi 2010 w Krakowie mamy ≈141 mm
    rain_block = [
        (6,6), # 6 h po 6mm/h - front pierwszy
        (12,3), # 12 h po 3 mm/h - dlugotrwaly deszcz
        (3,15), # 3h po 15 mm/h - najsilniejsze opady -> podtopienia
        (6,4) # 6h po 4 mm/h - schodzenie
    ]
    #-------------------------------------------------------------------------------------------

    # Evacuation simulation parameters -------------------------------------------------------
    graph_path = 'Data/krakow_roads2.graphml'
    dem_path = 'Data/krakow_merged.tif'
    n_agents = 150
    n_rescue_agents = 5
    G = build_example_graph(graph_path)
    #-------------------------------------------------------------------------------------------

    # Run evacuation simulation ---------------------------------------------------------------
    if run_evacuation_simulation:
        # create output folder with timestamp
        curr_time = datetime.now().strftime("%H_%M_%S")
        folder_path = f"output/run_{curr_time}"
        os.makedirs(folder_path, exist_ok=True)
        log_path = os.path.join(folder_path, "log.txt")

        flood_model = None
        if run_flood_simulation:
            flood_model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)
        model = Model(n_agents=n_agents, n_rescue_agents=n_rescue_agents, roads_graph=G, dem_path=dem_path, log_path=folder_path, flood_model=flood_model)
        
        for t in range(200):
            with open(log_path, "a") as f:
                f.write(f"\n--- Step {t} ---\n")
            print(f"--- Step {t} ---")
            model.step()

    # Run flood simulation (only if no evacuation) -------------------------------------------
    if run_flood_simulation and not run_evacuation_simulation:
        

        model = FloodModel(dem_path, k=k, area_bounds=area_bounds, rain_block=rain_block)

        plt.figure(figsize=(10,6))
        for t in range(len(model.rain_series)):
            model.step()

            # animacja co 20 kroków
            if t % 20 == 0:
                plt.clf()

                #plt.imshow(roads_rynek, cmap="binary", alpha=0.18, origin="upper")
                plt.imshow(model.roads, cmap="gray", alpha=0.3)
                plt.contour(model.roads, levels=[0.5], colors='black', linewidths=0.5)

                # terrain
                im1 = plt.imshow(model.area, cmap='terrain', origin='upper')
                # water overlay
                im2 = plt.imshow(model.water, cmap='Blues', alpha=0.65, origin='upper')

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
    
    if run_flood_simulation and run_validation:
        map_path = "Data/validation_krakow.tif"

        with rasterio.open(dem_path) as dem_src:
            dem_transform = dem_src.transform

        model_mask, reference_mask, metrics = validate_model_flood(
            map_path=map_path,
            model_height=model.area,
            model_water=model.water,
            model_transform=dem_transform
        )

        # --- 3. Print metrics ---
        print("\nValidation metrics:")
        for k, v in metrics.items():
            print(f"{k}: {v}")

        # --- 4. Optional: visualize model vs reference ---
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10,10))
        plt.imshow(model_mask, cmap="Blues", alpha=0.5)
        plt.imshow(reference_mask, cmap="Reds", alpha=0.5)
        plt.title("Model flood (blue) vs Reference flood (red)")
        plt.savefig("Data/validation_overlay.png")
        plt.close()

