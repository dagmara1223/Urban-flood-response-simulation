import mesa
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import random 
from citizens.citizen_agent import CitizenAgent, CitizenState
from call_center_agent import CallCenterAgent
from rescue_agent import RescueAgent

class TestModel(mesa.Model):
    def __init__(self, n_agents, n_rescue_agents, roads_graph):
        super().__init__()
        self.space = mesa.space.NetworkGrid(roads_graph) # Create a NetworkGrid based on the road graph
        self.create_agents(n=n_agents, n2=n_rescue_agents)
        self.call_center = CallCenterAgent(self)
        self.safety_spot = [n for n in self.space.G.nodes if n in [1, 13, 40]]  # Example of a safe spot node

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
        '''
        Maps water depth values to the graph nodes as an attribute.
        '''
        pass
        
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

        walk_edges = [(u, v) for u, v, d in self.space.G.edges(data=True) if d.get('road_type') in ['walk']]
        drive_edges = [(u, v) for u, v, d in self.space.G.edges(data=True) if d.get('road_type') in ['drive', 'both']]

        nx.draw_networkx_edges(self.space.G, pos, edgelist=walk_edges, edge_color='blue', width=2, label='Walkable Roads')
        nx.draw_networkx_edges(self.space.G, pos, edgelist=drive_edges, edge_color='black', width=2, label='Drivable Roads')


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
        plt.pause(2)


def build_example_graph():
    # Tworzenie TESTOWEGO grafu drogowego
    G = nx.read_graphml("../Data/krakow_roads.graphml")
    G = nx.convert_node_labels_to_integers(G)
    for n, data in G.nodes(data=True):
        data['pos'] = (float(data['x']), float(data['y']))
    return G


if __name__ == "__main__":
    G = build_example_graph()
    model = TestModel(n_agents=5, n_rescue_agents=2, roads_graph=G)

    for t in range(20):
        print(f"--- Step {t} ---")
        model.step()
        for a in model.agents:
            if isinstance(a, CitizenAgent):
                print(f"Agent {a.unique_id}: node={a.current_edge[0]}, state={a.state}")
            elif isinstance(a, RescueAgent):
                print(f"RescueAgent {a.unique_id}: node={a.current_edge[0]}, carrying={[c.unique_id for c in a.carrying]}")