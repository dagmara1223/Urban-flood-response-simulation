import mesa
import networkx as nx
import numpy as np
from citizens.citizen_agent import CitizenAgent, CitizenState
from rescue_agent import RescueAgent

class CallCenterAgent(mesa.Agent):
    """
    Central coordinator that assigns rescue agents to critically unsafe citizens.
    Responsibilities:
    - Monitor citizens' states and identify those needing rescue.
    - Assign available rescue agents to the closest critically unsafe citizens.
    Methods:
    - collect_unsafe_citizens: List of all citizens in a critically unsafe state.
    - assign_rescue_tasks: Assigns rescue agents to the closest critically unsafe citizens.
    - step: Executes the assignment of rescue tasks each simulation step.
    """
    def __init__(self, model):
        super().__init__(model)
        
    
    def collect_unsafe_citizens(self):
        return [a for a in self.model.agents if isinstance(a, CitizenAgent) and a.state == CitizenState.CRITICALLY_UNSAFE]

    def assign_rescue_tasks(self):
        citizens = self.collect_unsafe_citizens()
        rescuers = [a for a in self.model.agents if isinstance(a, RescueAgent)]

        for citizen in citizens:
            # check if someone is already on their way to this citizen
            already_assigned = any(
                r.target == citizen and len(r.carrying) < r.capacity for r in rescuers
            )
            if already_assigned:
                continue  # skip, someone is already on their way

            # select the closest available rescuer
            available = [r for r in rescuers if r.target is None and len(r.carrying) == 0]
            if not available:
                continue

            closest = min(
                available,
                key=lambda r: nx.shortest_path_length(self.model.space.G, r.current_edge[0], citizen.current_edge[0], weight="length")
            )
            closest.set_target(citizen)
            print(f"CallCenter assigned RescueAgent {closest.unique_id} → Citizen {citizen.unique_id}")

    def step(self):
        self.assign_rescue_tasks()
    
