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
from flood_agent.model.primitive_model import flood_step
import os
from datetime import datetime

class TestModel(mesa.Model):
    def __init__(self, n_agents, n_rescue_agents, roads_graph, dem_path, log_path):
        super().__init__()
        self.count = 0
        self.log_path = log_path
        self.space = mesa.space.NetworkGrid(roads_graph) # Create a NetworkGrid based on the road graph
        self.create_agents(n=n_agents, n2=n_rescue_agents)
        self.call_center = CallCenterAgent(self)
        self.safety_spot = [n for n in self.space.G.nodes if n in [13, 40]]  # Example of a safe spot node

        # --- Initialize flood model ---
        with rasterio.open(dem_path) as src:
            self.transform = src.transform
            self.height = src.read(1).astype(float)
            self.height[self.height == src.nodata] = np.nan
            self.height = np.nan_to_num(self.height, nan=np.nanmin(self.height))

        self.height = self.height[::10, ::10]  # region of interest
        self.water = np.zeros_like(self.height)
        self.water[100:150, 0:100] = 10.0 
        self.water[300:350, 0:100] = 10.0
        self.water[200:250, 200:300] = 10.0
        self.k = 0.12

        self.map_depth_to_graph()

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

    def map_depth_to_graph(self):
        nrows, ncols = self.water.shape
        
        # Get min/max coordinates from graph nodes
        pos_dict = nx.get_node_attributes(self.space.G, "pos")
        if not pos_dict:
            return
            
        xs = [pos[0] for pos in pos_dict.values()]
        ys = [pos[1] for pos in pos_dict.values()]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        with open(self.log_path, "a") as f:
            f.write(f"Graph bounds: x({x_min:.2f}, {x_max:.2f}), y({y_min:.2f}, {y_max:.2f})\n")
            f.write(f"Water array: {nrows} x {ncols}\n")
        
        # --- Map flood depths to road nodes ---
        for n, data in self.space.G.nodes(data=True):
            if "pos" not in data:
                data["depth"] = 0.0
                continue
                
            x, y = data["pos"]
            
            # Normalize coordinates to array indices
            col = int(((x - x_min) / (x_max - x_min)) * (ncols - 1))
            row = int(((y_max - y) / (y_max - y_min)) * (nrows - 1))
            
            # Ensure within bounds (should always be, but just in case)
            row = max(0, min(row, nrows - 1))
            col = max(0, min(col, ncols - 1))
            
            depth = float(self.water[row, col])
            data["depth"] = depth
            data['pos'] = (col, row)
    
    def flood_step(self):
        """
        Update flood simulation and map depth values to the road network.
        """
        # --- Flood update ---
        self.water = flood_step(self.height, self.water, k=self.k)

        for n, data in self.space.G.nodes(data=True):
            col, row = data['pos']
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
        pos = nx.get_node_attributes(G, "pos")        

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
    return G


if __name__ == "__main__":
    curr_time = datetime.now().strftime("%H_%M_%S")
    folder_path = f"output/run_{curr_time}"
    os.makedirs(folder_path, exist_ok=True)
    log_path = os.path.join(folder_path, "log.txt")

    graph_path = 'Data/krakow_roads.graphml'
    dem_path = 'Data/HighResolution.tiff'
    n_agents = 30
    n_rescue_agents = 5
    G = build_example_graph(graph_path)
    model = TestModel(n_agents=n_agents, n_rescue_agents=n_rescue_agents, roads_graph=G, dem_path=dem_path, log_path=log_path)
    
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