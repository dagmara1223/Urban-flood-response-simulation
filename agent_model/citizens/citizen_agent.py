import random
import mesa
from enum import Enum
import numpy as np
import matplotlib.pyplot as plt


class CitizenState(Enum):
    """
    Enum representing the safety state of a citizen.

    Attributes:
        SAFE (int): The citizen is in no need of immediate evacuation.
        UNSAFE (int): The citizen is in endangered area and needs to seek an evacuation.
        CRITICALLY_UNSAFE (int): The citizen is in a heavily flooded area and requires assistance to be rescued.
        RESCUED (int): The citizen has been rescued and is going to a safe location.
    """
    SAFE = 0
    UNSAFE = 1
    CRITICALLY_UNSAFE = 2
    RESCUED = 3

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
        current-speed (float): Current speed of an agent. Current speed cannot exceed maximum speed. When the agent is flooded or surrounded by too many other agents per grid, its speed decreases.

    """
    def __init__(self, model, start_node):
        super().__init__(model)
        self.current_edge = (start_node, None)  # current edge (start_node -> next_node)
        self.progress = 0.0  # 0 = at start_node, 1 = at next_node
        self.state = CitizenState.SAFE
        self.max_speed = np.random.normal(1.5, 0.3)
        self.speed = self.max_speed  # current speed
        print(f'I am an agent {self.unique_id}, hooray location: {self.current_edge} speed: {self.max_speed}')

    def update_state(self, water_matrix: np.ndarray):
        pass

    def evacuate(self):
        pass

    def step(self):
        if self.state == CitizenState.CRITICALLY_UNSAFE or self.state == CitizenState.RESCUED:
            return  # No action needed
        
        # DLA TESTÓW przemieszczania: losowy sąsiedni węzeł
        if self.current_edge[1] is None:
            # losowy wybór następnego węzła
            next_node = random.choice(list(self.model.space.get_neighborhood(self.current_edge[0])))
            self.current_edge = (self.current_edge[0], next_node)
            self.progress = 0.0
        
        # Idzie wzdłuż krawędzi
        edge_length = self.model.space.G[self.current_edge[0]][self.current_edge[1]]['length']
        self.progress += self.speed / edge_length
        
        if self.progress >= 1.0:
            # Dotarł do następnego węzła
            self.current_edge = (self.current_edge[1], None)
            self.progress = 0.0
            self.model.space.move_agent(self, self.current_edge[0])
