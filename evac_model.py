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

class TestModel(mesa.Model):
    def __init__(self, n_agents, n_rescue_agents, roads_graph, dem_path):
        super().__init__()
        self.space = mesa.space.NetworkGrid(roads_graph) # Create a NetworkGrid based on the road graph
        self.create_agents(n=n_agents, n2=n_rescue_agents)
        self.call_center = CallCenterAgent(self)
        self.safety_spot = [n for n in self.space.G.nodes if n in [1, 13, 40]]  # Example of a safe spot node

        # --- Initialize flood model ---
        with rasterio.open(dem_path) as src:
            self.transform = src.transform
            self.height = src.read(1).astype(float)
            self.height[self.height == src.nodata] = np.nan
            self.height = np.nan_to_num(self.height, nan=np.nanmin(self.height))

        self.height = self.height[800:1000, 900:1100]  # region of interest
        self.water = np.zeros_like(self.height)
        self.water[50:55, 90:95] = 50.0  # initial flooding
        self.k = 0.12

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
        """
        Update flood simulation and map depth values to the road network.
        """
        # --- Flood update ---
        self.water = flood_step(self.height, self.water, k=self.k)
        nrows, ncols = self.water.shape
        
        # Get min/max coordinates from graph nodes
        pos_dict = nx.get_node_attributes(self.space.G, "pos")
        if not pos_dict:
            return
            
        xs = [pos[0] for pos in pos_dict.values()]
        ys = [pos[1] for pos in pos_dict.values()]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        print(f"Graph bounds: x({x_min:.2f}, {x_max:.2f}), y({y_min:.2f}, {y_max:.2f})")
        print(f"Water array: {nrows} x {ncols}")
        
        # --- Map flood depths to road nodes ---
        for n, data in self.space.G.nodes(data=True):
            if "pos" not in data:
                data["depth"] = 0.0
                continue
                
            x, y = data["pos"]
            
            # Normalize coordinates to array indices
            col = int(((x - x_min) / (x_max - x_min)) * (ncols - 1))
            row = int(((y - y_min) / (y_max - y_min)) * (nrows - 1))
            
            # Ensure within bounds (should always be, but just in case)
            row = max(0, min(row, nrows - 1))
            col = max(0, min(col, ncols - 1))
            
            depth = float(self.water[row, col])
            data["depth"] = depth
            
            # Store array indices for debugging
            data["water_row"] = row
            data["water_col"] = col

        # --- Mark unsafe roads ---
        unsafe_edges = 0
        for u, v, d in self.space.G.edges(data=True):
            node_depth = max(
                self.space.G.nodes[u].get("depth", 0),
                self.space.G.nodes[v].get("depth", 0),
            )
            d["safe"] = "no" if node_depth > 3 else "yes"
            if node_depth > 3:
                unsafe_edges += 1
                
        print(f"Unsafe edges: {unsafe_edges}/{self.space.G.number_of_edges()}")
        
    def step(self):
        self.map_depth_to_graph() # Update water depth on graph nodes, not shure if should be done every step

        self.call_center.step()

        for i in range(10): # na razie testowo 10 substeps per step
            self.agents.do("step")
        self.visualise_step() # Visualize the current state of the model, just for testing

    def visualise_step(self):
        ax = self.ax
        ax.clear()

        pos = nx.get_node_attributes(self.space.G, "pos")
        nx.draw_networkx_nodes(self.space.G, pos, nodelist=self.safety_spot, node_size=100, label='Safe Nodes', node_color='green')

        safe_edges = [(u, v) for u, v, d in self.space.G.edges(data=True) if d.get('safe') in ['yes']]
        unsafe_edges = [(u, v) for u, v, d in self.space.G.edges(data=True) if d.get('safe') in ['no']]

        nx.draw_networkx_edges(self.space.G, pos, edgelist=safe_edges, edge_color='black', width=2, label='Safe Roads')
        nx.draw_networkx_edges(self.space.G, pos, edgelist=unsafe_edges, edge_color='red', width=2, label='Unsafe Roads')


        # Wizualizacja agentów
        agent_positions_x = []
        agent_positions_y = []
        rescue_agents_x = []
        rescue_agents_y = []
        for agent in self.agents:
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

        plt.scatter(agent_positions_x, agent_positions_y, c='red', s=50, label='Agents', zorder=2)
        plt.scatter(rescue_agents_x, rescue_agents_y, c='purple', s=50, label='Rescue Agents', zorder=2)
        plt.legend()
        plt.title("Road network with agents")

        plt.draw()  # Update figure
        plt.pause(1)


def build_example_graph():
    # Tworzenie TESTOWEGO grafu drogowego
    G = nx.read_graphml("Data/krakow_roads.graphml")
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']), float(data['y']))
    return G


if __name__ == "__main__":
    G = build_example_graph()
    dem_path = 'Data/StandardResolution.tiff'
    model = TestModel(n_agents=30, n_rescue_agents=5, roads_graph=G, dem_path=dem_path)
    
    for t in range(200):
        print(f"--- Step {t} ---")
        model.step()
        for a in model.agents:
            if isinstance(a, CitizenAgent):
                print(f"Agent {a.unique_id}: node={a.current_edge[0]}, state={a.state}")
            elif isinstance(a, RescueAgent):
                print(f"RescueAgent {a.unique_id}: node={a.current_edge[0]}, carrying={[c.unique_id for c in a.carrying]}")