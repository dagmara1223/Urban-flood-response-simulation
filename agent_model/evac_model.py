import mesa
import numpy as np
import matplotlib.pyplot as plt
from citizens.citizen_agent import CitizenAgent
import networkx as nx
import random 

class TestModel(mesa.Model):
    def __init__(self, n_agents, roads_graph):
        super().__init__()
        self.roads = roads_graph # Store the road network graph
        self.create_agents(n=n_agents)
        self.safety_spot = ["C"]  # Example of a safe spot node
        
    def create_agents(self, n: int):
        # Create 'n' citizen agents and assign them random starting nodes
        # TODO: Should be changed to realistic start positions
        for i in range(n):
            start_node = random.choice(list(self.roads.nodes))
            agent = CitizenAgent(self, start_node=start_node)
            self.agents.add(agent)

    def map_depth_to_graph(self):
        '''
        Maps water depth values to the graph nodes as an attribute.
        '''
        pass
        
    def step(self):
        self.map_depth_to_graph() # Update water depth on graph nodes, not shure if should be done every step
        self.agents.do("step")
        self.visualise_step() # Visualize the current state of the model, just for testing

    def visualise_step(self):
        pos = nx.get_node_attributes(self.roads, "pos")
        node_colors = ["green" if node in self.safety_spot else "skyblue" for node in self.roads.nodes]
        nx.draw(self.roads, pos, node_color=node_colors, with_labels=True, node_size=500, font_weight="bold")

        # Wizualizacja agentów
        agent_positions_x = []
        agent_positions_y = []
        for agent in self.agents:
            x0, y0 = pos[agent.current_edge[0]]
            if agent.current_edge[1] is not None:
                x1, y1 = pos[agent.current_edge[1]]
                x = x0 + (x1 - x0) * agent.progress
                y = y0 + (y1 - y0) * agent.progress
            else:
                x, y = x0, y0
            agent_positions_x.append(x + np.random.uniform(-0.05, 0.05))  # slight random offset for visibility
            agent_positions_y.append(y + np.random.uniform(-0.05, 0.05))

        plt.scatter(agent_positions_x, agent_positions_y, c='red', s=200, label='Agents', zorder=2)
        plt.legend()
        plt.title("Road network with agents")
        plt.show()



def build_example_graph():
    # Tworzenie TESTOWEGO grafu drogowego
    G = nx.Graph()
    # Węzły z pozycjami
    G.add_node("A", pos=(0, 0))
    G.add_node("B", pos=(2, 0))
    G.add_node("C", pos=(4, 0))
    G.add_node("D", pos=(2, 2))
    # Krawędzie (drogi)
    G.add_edge("A", "B", length=20) # można dodać więcej atrybutów jak szerokość drogi, max prędkość idk.
    G.add_edge("B", "C", length=20)
    G.add_edge("B", "D", length=20)
    G.add_edge("C", "D", length=30)
    return G


if __name__ == "__main__":
    G = build_example_graph()
    model = TestModel(n_agents=5, roads_graph=G)
    model.visualise_step()

    for t in range(20):
        print(f"--- Step {t} ---")
        model.step()
        for a in model.agents:
            print(f"Agent {a.unique_id}: node={a.current_edge[0]}, state={a.state}")