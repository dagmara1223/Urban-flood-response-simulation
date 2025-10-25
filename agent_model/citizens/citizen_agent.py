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
        current-speed (float): Current speed of an agent. Current speed cannot exceed maximum speed. When the agent is flooded or surrounded by too many other agents per grid, its speed decreases.

    """
    def __init__(self, model, max_x: float, max_y: float):
        super().__init__(model)
        self.x = np.random.random() * max_x
        self.max_x = max_x
        self.y = np.random.random() * max_y
        self.max_y = max_y
        self.state = CitizenState.SAFE
        self.max_speed = np.random.normal(1.5, 0.3)
        print(f'I am an agent, hooray x: {self.x} y: {self.y} speed: {self. max_speed}')

    def update_state(self, water_matrix: np.ndarray):
        pass

    def evacuate(self):
        pass

class TestModel(mesa.Model):
    def __init__(self, n_agents, obstacles_matrix: np.ndarray):
        super().__init__()
        self.space = mesa.space.ContinuousSpace(50, 50, torus=False)
        TestModel.create_agents(self, n=n_agents)
        self.safety_spot = (np.random.random() * 50, np.random.random() * 50)
        print(f'Safety spot: {self.safety_spot}')
        self.obstacle_matrix = obstacles_matrix

    def create_agents(self, n: int):
        for i in range(n):
            agent = CitizenAgent(self, 50, 50)
            self.space.place_agent(agent, (agent.x, agent.y))

    def visualise_step(self):
        positions = [agent.pos for agent in self.space._agent_to_index.keys()]
        xs, ys = zip(*positions)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(xs, ys, c="blue", s=30, alpha=0.7)
        ax.set_xlim(0, 50)
        ax.set_ylim(0, 50)

        for i in range(self.obstacle_matrix.shape[0]):
            for j in range(self.obstacle_matrix.shape[1]):
                if obstacle_matrix[i][j] == 1:
                    rect = plt.Rectangle((i, j), 1, 1, color="gray")
                    ax.add_patch(rect)

        ax.set_title("Current map")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True)
        plt.show()

obstacle_matrix = np.zeros(shape=(50,50))
for i in range(20):
    obstacle_matrix[15+i][i] = 1
    obstacle_matrix [10+i][30] = 1
model = TestModel(10, obstacle_matrix)
#for _ in range(100):
#    model.step()
model.visualise_step()