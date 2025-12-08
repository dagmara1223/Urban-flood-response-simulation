import mesa
import numpy as np
import networkx as nx
from agent_model.citizens.citizen_agent import CitizenAgent, CitizenState

class RescueState:
    """Enum-like class for rescue agent states."""
    AVAILABLE = 0       # Ready for new mission
    ON_MISSION = 1      # Heading to citizen
    CARRYING = 2        # Carrying rescued citizens


class RescueAgent(mesa.Agent):
    """
    Rescue agent representing emergency services (fire, ambulance).
    Drives along the road network to rescue citizens and deliver them to safety.
    """

    def __init__(self, model, start_node):
        super().__init__(model)
        self.current_edge = (start_node, None)
        self.progress = 0.0
        self.speed = np.random.normal(9.0, 1.0) * 10 # driving only, speed in m/s, 10 seconds per step
        self.capacity = 2
        self.carrying = []
        self.target = None
        self.path = []
        self.state = RescueState.AVAILABLE

        self.rescue_start_times = {}  # citizen_id -> start time


    def set_target(self, citizen):
        """Assign a new target (citizen) and compute a path avoiding unsafe roads."""
        self.target = citizen
        G = self.model.space.G
        if citizen.unique_id not in self.rescue_start_times:
            self.rescue_start_times[citizen.unique_id] = self.model.count

        # Create a subgraph that only includes safe edges
        safe_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("safe", "yes") == "yes"]
        subG = G.edge_subgraph(safe_edges).copy()

        try:
            path = nx.shortest_path(subG, self.current_edge[0], citizen.current_edge[0], weight="length")
            self.path = path
            if len(path) > 1:
                self.current_edge = (self.current_edge[0], path[1])
            self.state = RescueState.ON_MISSION
        except Exception:
            try:
                path = nx.shortest_path(G, self.current_edge[0], citizen.current_edge[0], weight="length")
                self.path = path
                if len(path) > 1:
                    self.current_edge = (self.current_edge[0], path[1])
                self.state = RescueState.ON_MISSION
                
            except Exception:
                self.path = []
                self.target = None
                self.state = RescueState.AVAILABLE

    def move_along_path(self):
        """Move along the current path according to speed and edge length."""
        if not self.path or len(self.path) < 2:
            return

        remaining_distance = self.speed  # ile agent może przejechać w tym kroku
        water_depth = self.model.space.G.nodes[self.current_edge[0]].get("depth", 0)
        if water_depth > 0.1:
            remaining_distance = self.speed * np.exp(-2 * water_depth)
            remaining_distance = max(remaining_distance, 2.0 * 10)  # min speed 2 m/s
        G = self.model.space.G

        while remaining_distance > 0 and len(self.path) >= 2:
            start = self.path[0]
            next_node = self.path[1]
            edge_length = G[start][next_node]["length"]

            distance_to_next = edge_length * (1.0 - self.progress)
            if remaining_distance >= distance_to_next:
                # Przechodzimy przez węzeł
                remaining_distance -= distance_to_next
                self.current_edge = (next_node, self.path[2] if len(self.path) > 2 else None)
                self.model.space.move_agent(self, next_node)
                self.path.pop(0)
                self.progress = 0.0

                # Synchronizacja obywateli w środku pojazdu
                for c in self.carrying:
                    self.model.space.move_agent(c, next_node)
            else:
                # Poruszamy się w obrębie krawędzi
                self.progress += remaining_distance / edge_length
                remaining_distance = 0

        # Aktualizacja pozycji obywateli w środku pojazdu
        for c in self.carrying:
            c.current_edge = self.current_edge
            c.progress = self.progress

    def rescue(self):
        """Rescue citizens at current location if possible."""
        cellmates = self.model.space.get_cell_list_contents([self.current_edge[0]])
        for a in cellmates:
            if isinstance(a, CitizenAgent) and a.state == CitizenState.CRITICALLY_UNSAFE:
                if len(self.carrying) < self.capacity:
                    a.state = CitizenState.RESCUED
                    self.carrying.append(a)
                    self.state = RescueState.CARRYING
                    self.target = None

                    start_step = self.rescue_start_times.pop(a.unique_id, self.model.count)
                    evac_time_to_rescuer = self.model.count - start_step
                    self.model.stats["rescue_response_time"].append(evac_time_to_rescuer)
                    self.rescue_start_times[a.unique_id] = self.model.count

                    # Compute route to nearest safe location
                    safe = min(
                        self.model.safety_spot,
                        key=lambda n: nx.shortest_path_length(
                            self.model.space.G,
                            self.current_edge[0],
                            n,
                            weight="length",
                        ),
                    )
                    safe_edges = [(u, v) for u, v, d in self.model.space.G.edges(data=True) if d.get("safe", "yes") == "yes"]
                    subG = self.model.space.G.edge_subgraph(safe_edges).copy()
                    try:
                        self.path = nx.shortest_path(subG, self.current_edge[0], safe, weight="length")
                    except Exception:
                        self.path = nx.shortest_path(self.model.space.G, self.current_edge[0], safe, weight="length")

                    return

    def step(self):
        """Main agent behavior each simulation step."""
        # Case 1: carrying citizens → go to safety
        if self.state == RescueState.CARRYING:
            if self.current_edge[0] in self.model.safety_spot:
                for c in self.carrying:
                    c.state = CitizenState.SAFE

                    start_step = self.rescue_start_times.pop(c.unique_id, self.model.count)
                    evac_time = self.model.count - start_step
                    self.model.stats["rescue_to_safety_time"].append(evac_time)
                self.carrying.clear()
                self.state = RescueState.AVAILABLE
            else:
                self.move_along_path()
            return

        # Case 2: on mission → move and rescue if at citizen
        if self.state == RescueState.ON_MISSION and self.target:
            if self.path:
                self.move_along_path()
            self.rescue()

        # Case 3: idle → wait for assignment
        if self.state == RescueState.AVAILABLE:
            return
