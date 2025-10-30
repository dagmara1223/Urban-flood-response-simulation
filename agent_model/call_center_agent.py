import networkx as nx
from agent_model.citizens.citizen_agent import CitizenAgent, CitizenState
from agent_model.rescue_agent import RescueAgent, RescueState

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
                with open(self.model.log_path, "a") as f:
                    f.write(f"[CallCenter] Assigned RescueAgent {closest.unique_id} -> Citizen {citizen.unique_id}\n")
            except nx.NetworkXNoPath:
                continue

    def step(self):
        """Execute task assignments each model step."""
        self.assign_rescue_tasks()
