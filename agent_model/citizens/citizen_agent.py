import mesa
from enum import Enum

class CitizenAgent(mesa.Agent):
    """
    Agent model representing the citizens during the flood.

    Attributes:
        state (CitizenState): Stores the safety state of the citizen.
            - `CitizenState.SAFE`: The citizen is safe area.
            - `CitizenState.UNSAFE`: The citizen is in mildly unsafe area and needs to seek an evacuation
            - `CitizenState.CRITICALLY_UNSAFE`: The citizen is in a heavily flooded area and requires assistance to be rescued.
    """
    def __init__(self, model, state: CitizenState):
        super().__init__(model)
        self.state = state

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
