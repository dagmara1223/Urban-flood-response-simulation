import mesa
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import random 
import rasterio
from rasterio.transform import rowcol
from agent_model.citizens.citizen_agent import CitizenAgent
from agent_model.call_center_agent import CallCenterAgent
from agent_model.rescue_agent import RescueAgent
#from flood_agent.model.model import flood_step
import os
from datetime import datetime

class TestModel(mesa.Model):
    def __init__(self, n_agents, n_rescue_agents, roads_graph, dem_path, log_path):
        super().__init__()
        self.count = 0
        self.log_path = os.path.join(log_path, "log.txt")
        self.log_path_time = os.path.join(log_path, "evac_time.txt")

        self.space = mesa.space.NetworkGrid(roads_graph) # Create a NetworkGrid based on the road graph
        self.create_agents(n=n_agents, n2=n_rescue_agents)
        self.call_center = CallCenterAgent(self)
        self.safety_spot = [n for n in self.space.G.nodes if n in [13, 40]]  # Example of a safe spot node

        self.water_maps = self.load_water_maps("Data")
        self.nrows, self.ncols = self.water_maps[0].shape

        with rasterio.open("krakow_merged.tif") as src:
            height = src.read(1)
        self.height = height[2000:3200, 3500:4800]
        self.height = self.height[::6, ::6]

        # mapowanie pierwszego kroku
        self.water = self.water_maps[0]

    def load_water_maps(self, folder_path):
        """Wczytuje wszystkie zapisane pliki .npy z symulacji powodzi i sortuje je rosnąco po numerze kroku"""
        files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith(".npy")],
            key=lambda x: int(x.split("_")[-1].split(".")[0])
        )
        water_maps = [np.load(os.path.join(folder_path, f)) for f in files]
        return water_maps
    
    def create_agents(self, n: int, n2: int):
        # Create 'n' citizen agents and assign them random starting nodes
        # TODO: Should be changed to realistic start positions

        for i in range(n2):
            start_node = random.choice(list(self.space.G.nodes))
            agent = RescueAgent(self, start_node=start_node)
            self.agents.add(agent)
            self.space.place_agent(agent, start_node)

        for i in range(n):
            start_node = random.choice(list(self.space.G.nodes))
            agent = CitizenAgent(self, start_node=start_node)
            self.agents.add(agent)
            self.space.place_agent(agent, start_node)

        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(10, 10))

    
    def flood_step(self):
        """
        Update flood simulation and map depth values to the road network.
        """
        # --- Flood update ---
        if self.count < len(self.water_maps):
            self.water = self.water_maps[self.count]
        else:
            self.water = self.water_maps[-1]

        for n, data in self.space.G.nodes(data=True):
            col, row = data['pos_array']
            depth = float(self.water[row, col])
            data["depth"] = depth

        # --- Mark unsafe roads ---
        unsafe_edges = 0
        for u, v, d in self.space.G.edges(data=True):
            node_depth = max(
                self.space.G.nodes[u].get("depth", 0),
                self.space.G.nodes[v].get("depth", 0),
            )
            d["safe"] = "no" if node_depth > 0.5 else "yes"
            if node_depth > 0.5:
                unsafe_edges += 1
                
        with open(self.log_path, "a") as f:
            f.write(f"Unsafe edges: {unsafe_edges}/{self.space.G.number_of_edges()}\n")
        
    def step(self):
        if self.count%5 == 0:
            self.flood_step() # Update water depth on graph nodes, not shure if should be done every step

        if self.count%5 == 0:
            self.call_center.step()

        
        self.agents.do("step")
        self.visualise_step() # Visualize the current state of the model, just for testing
        
        self.count += 1

    def visualise_step(self):
        ax = self.ax
        ax.clear()
        G = self.space.G
        safety_spot = self.safety_spot
        agents = self.agents
        pos = nx.get_node_attributes(G, "pos_array")        

        safe_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('safe') in ['yes']]
        unsafe_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('safe') in ['no']]

        # Wizualizacja agentów
        agent_positions_x = []
        agent_positions_y = []
        rescue_agents_x = []
        rescue_agents_y = []
        for agent in agents:
            if not isinstance(agent, (CitizenAgent, RescueAgent)):
                continue
            x0, y0 = pos[agent.current_edge[0]]
            if agent.current_edge[1] is not None:
                x1, y1 = pos[agent.current_edge[1]]
                x = x0 + (x1 - x0) * agent.progress
                y = y0 + (y1 - y0) * agent.progress
            else:
                x, y = x0, y0
            if isinstance(agent, RescueAgent):
                rescue_agents_x.append(x)
                rescue_agents_y.append(y)
                continue
            agent_positions_x.append(x)
            agent_positions_y.append(y)

        ax.imshow(self.height, cmap='terrain', origin='upper') 
        ax.imshow(self.water, cmap='Blues', alpha=0.6, origin='upper', vmin=0, vmax=np.max(self.water)/3)
        
        nx.draw_networkx_nodes(G, pos, nodelist=safety_spot, node_size=100, label='Safe Nodes', node_color='green')
        nx.draw_networkx_edges(G, pos, edgelist=safe_edges, edge_color='black', width=2, label='Safe Roads')
        nx.draw_networkx_edges(G, pos, edgelist=unsafe_edges, edge_color='red', width=2, label='Unsafe Roads')

        plt.scatter(agent_positions_x, agent_positions_y, c='blue', s=20, label='Agents', zorder=2)
        plt.scatter(rescue_agents_x, rescue_agents_y, c='purple', s=20, label='Rescue Agents', zorder=2)

        plt.legend()
        plt.title("Road network with agents")

        plt.draw()  # Update figure
        plt.pause(0.2)


def build_example_graph(path):
    # Tworzenie TESTOWEGO grafu drogowego
    G = nx.read_graphml(path)
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']), float(data['y']))
        data['pos_array'] = (int(data['pos_array_x']), int(data['pos_array_y']))
    return G


if __name__ == "__main__":
    curr_time = datetime.now().strftime("%H_%M_%S")
    folder_path = f"output/run_{curr_time}"
    os.makedirs(folder_path, exist_ok=True)
    log_path = os.path.join(folder_path, "log.txt")

    graph_path = 'Data/krakow_roads2.graphml'
    dem_path = 'krakow_merged.tif'

    n_agents = 30
    n_rescue_agents = 5
    G = build_example_graph(graph_path)
    model = TestModel(n_agents=n_agents, n_rescue_agents=n_rescue_agents, roads_graph=G, dem_path=dem_path, log_path=folder_path)
    
    for t in range(200):
        with open(log_path, "a") as f:
            f.write(f"\n--- Step {t} ---\n")
        print(f"--- Step {t} ---")
        model.step()
        for a in model.agents:
            if isinstance(a, CitizenAgent):
                with open(log_path, "a") as f:
                    f.write(f"Agent {a.unique_id}: node={a.current_edge[0]}, state={a.state}\n")
            elif isinstance(a, RescueAgent):
                with open(log_path, "a") as f:
                    f.write(f"RescueAgent {a.unique_id}: node={a.current_edge[0]}, carrying={[c.unique_id for c in a.carrying]}\n")