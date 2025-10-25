import mesa
import numpy as np
from citizens.citizen_agent import CitizenAgent, CitizenState 
import networkx as nx

class RescueAgent(mesa.Agent):
    """
    Agent representing a rescue unit (e.g., fire department, ambulance).

    Responsibilities:
    - Move along the road graph to reach citizens in need.
    - Rescue critically unsafe citizens and transport them to safe nodes.
    - Switch between driving and walking modes based on road accessibility.
    Attributes:
    - current_edge (tuple): A tuple representing the current edge the agent is on, consisting of the start and end nodes.
    - progress (float): A float indicating the agent's progress along the current edge, start node -> end node.
    - speed_drive (float): The driving speed of the rescue agent in m/s.
    - speed_walk (float): The walking speed of the rescue agent in m/s.
    - speed (float): The current speed of the agent, driving/walking.
    - capacity (int): An integer representing the maximum number of citizens that the agent can carry at one time.
    - carrying (list): A list that contains the citizens currently being carried by the agent.
    - target (CitizenAgent): The citizen that the agent is currently targeting for rescue.
    - path (list): A list of nodes representing the path that the agent will follow to reach the target citizen.
    Methods:
    - set_target(citizen): assign a citizen target and compute a path to the citizen.
    - shortest_path(G, start, goal, allowed_types=['drive','both','walk']): compute shortest path using only allowed road types; return None if no path.
    - move_along_path(): advance along the current path according to speed; update current edge, progress and move carried citizens.
    - rescue(): pick up critically unsafe citizens at the current node (if capacity allows), mark them RESCUED and plan route to nearest safety spot.
    - step(): per-tick behavior: deliver carried citizens to safety, move toward assigned target, and attempt rescue.
    """

    def __init__(self, model, start_node):
        super().__init__(model)
        self.current_edge = (start_node, None)
        self.progress = 0.0

        self.speed_drive = np.random.normal(8.0, 1.0)
        self.speed_walk = np.random.normal(1.3, 0.3)
        self.speed = self.speed_drive
        self.mode = "drive"

        self.capacity = 2
        self.carrying = []
        self.target = None
        self.path = []
        print(f"RescueAgent {self.unique_id} ready at {start_node}")

    
    def set_target(self, citizen):
        """Assigns a new target (citizen) and computes the route."""
        self.target = citizen
        G = self.model.space.G
        path = self.shortest_path(G, self.current_edge[0], citizen.current_edge[0])
        self.path = path or []
        if path:
            print(f"RescueAgent {self.unique_id} assigned path to Citizen {citizen.unique_id}: {len(path)} steps")
            self.current_edge = (self.current_edge[0], path[1] if len(path) > 1 else None)

    def shortest_path(self, G, start, goal, allowed_types=['drive', 'both', 'walk']):
        """Shortest path using only selected road types."""
        sub = G.edge_subgraph([
            (u, v) for u, v, d in G.edges(data=True)
            if d.get("road_type") in allowed_types
        ])
        try:
            return nx.shortest_path(sub, start, goal, weight="length")
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound as e:
            return None

    def move_along_path(self):
        if not self.path or len(self.path) < 2:
            return

        next_node = self.path[1]
        G = self.model.space.G
        edge_length = G[self.path[0]][next_node]['length']
        self.progress += self.speed / edge_length

        if self.progress >= 1.0:
            # arrived at the next node
            self.current_edge = (next_node, self.path[2] if len(self.path) > 2 else None)
            self.model.space.move_agent(self, next_node)
            self.path.pop(0)
            self.progress = 0.0
            for c in self.carrying:
                self.model.space.move_agent(self, next_node)

        # update positions of carried citizens
        for c in self.carrying:
            c.current_edge = self.current_edge
            c.progress = self.progress

    def rescue(self):
        """Recue citizens on this node."""
        cellmates = self.model.space.get_cell_list_contents([self.current_edge[0]])
        for a in cellmates:
            if isinstance(a, CitizenAgent) and a.state == CitizenState.CRITICALLY_UNSAFE:
                if len(self.carrying) < self.capacity:
                    a.state = CitizenState.RESCUED 
                    self.carrying.append(a)
                    print(f"RescueAgent {self.unique_id} rescued Citizen {a.unique_id} (now RESCUED)")
                    self.target = None
                    self.path = []
                    safe = min(self.model.safety_spot, key=lambda n: 
                               nx.shortest_path_length(self.model.space.G, self.current_edge[0], n, weight="length"))
                    self.path = nx.shortest_path(self.model.space.G, self.current_edge[0], safe, weight="length")

    def step(self):
        # if carrying citizens -> go to a safety point
        if self.carrying:
            if self.current_edge[0] in self.model.safety_spot:
                print(f"RescueAgent {self.unique_id} dropped off {len(self.carrying)} citizens.")
                for c in self.carrying:
                    c.state = CitizenState.SAFE
                self.carrying.clear()
            else:
                self.move_along_path()
            return

        # if assigned a citizen -> go to them
        if self.target:
            if self.path:
                self.move_along_path()
            self.rescue()
