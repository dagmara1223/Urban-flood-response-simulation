import mesa
from enum import Enum
import numpy as np


class CitizenState(Enum):
    """
    Enum representing the safety state of a citizen.

    Attributes:
        SAFE (int): The citizen is in no need of immediate evacuation.
        UNSAFE (int): The citizen is in endangered area and needs to seek an evacuation.
        CRITICALLY_UNSAFE (int): The citizen is in a heavily flooded area and requires assistance to be rescued.
    """
    SAFE = 0
    UNSAFE = 1
    CRITICALLY_UNSAFE = 2
class CitizenAgent(mesa.Agent):
    """
    Agent model representing the citizens during the flood.

    Attributes:
        state (CitizenState): Stores the safety state of the citizen.
            - `CitizenState.SAFE`: The citizen is safe area.
            - `CitizenState.UNSAFE`: The citizen is in mildly unsafe area and needs to seek an evacuation
            - `CitizenState.CRITICALLY_UNSAFE`: The citizen is in a heavily flooded area and requires assistance to be rescued.
        max_speed (float): Maximum speed of an agent in meters per second. The agent receives a randomized speed, when it is created.
            - it is calculated following a Gaussian distribution with mean = 1.5 m/s, std = 0.3 m/s
        current-speed (float): Current speed of an agent. Current speed cannot exceed maximum speed. When the agent is flooded, its speed decreases.

    """
    def __init__(self, model, state: CitizenState):
        super().__init__(model)
        self.state = state
        self.max_speed = np.random.normal(1.5, 0.3)

    def update_state(self, water_matrix: np.ndarray):
        pass

    def evacuate(self):
        pass

class TestModel(mesa.Model):
    def __init__(self, n_agents):
        super().__init__()
        self.space = mesa.space.ContinuousSpace(50, 50, torus=False)

model = TestModel()
for _ in range(100):
    model.step()