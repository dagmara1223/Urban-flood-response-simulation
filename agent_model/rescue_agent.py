import mesa
import numpy as np
import networkx as nx
from agent_model.citizens.citizen_agent import CitizenAgent, CitizenState


class RescueState:
    """Enum-like class for rescue agent states."""
    AVAILABLE = 0       # Ready for new mission
    ON_MISSION = 1      # Heading to citizen
    CARRYING = 2        # Carrying rescued citizens


class CallCenterAgent:
    """
    Central coordination unit (not a Mesa agent).
    Responsibilities:
    - Identify citizens in critical danger.
    - Assign available rescue agents to the closest unsafe citizens.
    - Track rescue states to avoid duplicate assignments.
    """

    def __init__(self, model):
        self.model = model

    def collect_unsafe_citizens(self):
        """Return list of citizens that are critically unsafe."""
        return [
            a for a in self.model.agents
            if isinstance(a, CitizenAgent) and a.state == CitizenState.CRITICALLY_UNSAFE
        ]

    def assign_rescue_tasks(self):
        citizens = self.collect_unsafe_citizens()
        rescuers = [
            a for a in self.model.agents
            if isinstance(a, RescueAgent)
        ]

        for citizen in citizens:
            # Skip if any rescuer already heading toward this citizen
            already_assigned = any(
                r.target == citizen and r.state in [RescueState.ON_MISSION, RescueState.CARRYING]
                for r in rescuers
            )
            if already_assigned:
                continue

            # Find available rescuers
            available = [r for r in rescuers if r.state == RescueState.AVAILABLE]
            if not available:
                continue

            # Choose the closest rescuer
            try:
                closest = min(
                    available,
                    key=lambda r: nx.shortest_path_length(
                        self.model.space.G,
                        r.current_edge[0],
                        citizen.current_edge[0],
                        weight="length",
                    ),
                )
                closest.set_target(citizen)
                print(f"[CallCenter] Assigned RescueAgent {closest.unique_id} → Citizen {citizen.unique_id}")
            except nx.NetworkXNoPath:
                continue

    def step(self):
        """Execute task assignments each model step."""
        self.assign_rescue_tasks()


class RescueAgent(mesa.Agent):
    """
    Rescue agent representing emergency services (fire, ambulance).
    Drives along the road network to rescue citizens and deliver them to safety.
    """

    def __init__(self, model, start_node):
        super().__init__(model)
        self.current_edge = (start_node, None)
        self.progress = 0.0
        self.speed = np.random.normal(8.0, 1.0)  # driving only
        self.capacity = 2
        self.carrying = []
        self.target = None
        self.path = []
        self.state = RescueState.AVAILABLE

        print(f"[RescueAgent {self.unique_id}] Ready at node {start_node}")

    def set_target(self, citizen):
        """Assign a new target (citizen) and compute a path avoiding unsafe roads."""
        self.target = citizen
        G = self.model.space.G

        # Create a subgraph that only includes safe edges
        safe_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("safe", "yes") == "yes"]
        subG = G.edge_subgraph(safe_edges).copy()

        try:
            path = nx.shortest_path(subG, self.current_edge[0], citizen.current_edge[0], weight="length")
            self.path = path
            if len(path) > 1:
                self.current_edge = (self.current_edge[0], path[1])
            self.state = RescueState.ON_MISSION
            print(f"[RescueAgent {self.unique_id}] Safe path to citizen {citizen.unique_id}: {len(path)} steps")
        except Exception:
            print(f"[RescueAgent {self.unique_id}] No SAFE path to Citizen {citizen.unique_id}")
            self.path = []
            self.target = None
            self.state = RescueState.AVAILABLE

    def move_along_path(self):
        """Move along the current path according to speed and edge length."""
        if not self.path or len(self.path) < 2:
            return

        next_node = self.path[1]
        G = self.model.space.G
        edge_length = G[self.path[0]][next_node]["length"]
        self.progress += self.speed / edge_length

        if self.progress >= 1.0:
            # Arrived at the next node
            self.current_edge = (next_node, self.path[2] if len(self.path) > 2 else None)
            self.model.space.move_agent(self, next_node)
            self.path.pop(0)
            self.progress = 0.0

            for c in self.carrying:
                self.model.space.move_agent(c, next_node)

        # Synchronize carried citizens
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
                    print(f"[RescueAgent {self.unique_id}] Rescued Citizen {a.unique_id}")

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
                print(f"[RescueAgent {self.unique_id}] Dropped off {len(self.carrying)} citizens at safety.")
                for c in self.carrying:
                    c.state = CitizenState.SAFE
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
