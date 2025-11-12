import random
import mesa
from enum import Enum

import networkx as nx
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

class CitizenDecisionMakingMode(Enum):
    """
    Enum representing the path finding algorithm the citizen uses to decide the evacuation path.

    Attributes:
        DIJIKSTRA: Citizen uses A star algorithm to find a path to safe node.
        RANDOM: Known also as a panic mode, the citizen picks the path to follow at random and hopes for the best.
        FOLLOWER: Citizen follows the nearest agent.
    """
    DIJIKSTRA = 0
    RANDOM = 1
    FOLLOWER = 2

class CitizenAgent(mesa.Agent):
    """
    Agent model representing the citizens during the flood.

    Attributes:
        current-edge (tuple): The edge the citizen is currently on (start_node -> next_node). If next_node is None, the citizen
                            has just reached the node and is about to calculate the next target.

        progress (float): How far the agent is on the current edge. 0 = at start_node, 1 = at next_node

        state (CitizenState): Stores the safety state of the citizen.
            - `CitizenState.SAFE`: The citizen is safe area.
            - `CitizenState.UNSAFE`: The citizen is in mildly unsafe area and needs to seek an evacuation
            - `CitizenState.CRITICALLY_UNSAFE`: The citizen is in a heavily flooded area and requires assistance to be rescued.

        decision_making_mode (CitizenDecisionMakingMode): Defines a heuristic the agent follows to find path to the safe node.
            - 'CitizenDecisionMakingMode.DIJIKSTRA': Path is found via DIJIKSTRA algorithm
            - 'CitizenDecisionMakingMode.RANDOM': Agent makes direction decision at random, also known as panick mode
            - 'CitizenDecisionMakingMode.FOLLOWER': Agent follows the nearest agent that is also not a follower.

        max_speed (float): Maximum speed of an agent in meters per second. The agent receives a randomized speed, when it is created.
            - it is calculated following a Gaussian distribution with mean = 1.5 m/s, std = 0.3 m/s

        current-speed (float): Current speed of an agent. Current speed cannot exceed maximum speed. When the agent is flooded or surrounded by too many other agents per grid, its speed decreases.

    """
    def __init__(self, model, start_node):
        super().__init__(model)
        self.current_edge = (start_node, None)  # current edge (start_node -> next_node)
        self.progress = 0.0  # 0 = at start_node, 1 = at next_node

        self.state = CitizenState.UNSAFE
        self.decision_making_mode = random.choice([CitizenDecisionMakingMode.RANDOM, CitizenDecisionMakingMode.DIJIKSTRA, CitizenDecisionMakingMode.DIJIKSTRA,
                                                   CitizenDecisionMakingMode.FOLLOWER, CitizenDecisionMakingMode.FOLLOWER])

        self.max_speed = np.random.normal(1.5, 0.3)
        self.current_speed = self.max_speed

        with open(self.model.log_path, "a") as f:
                    f.write(f'I am an agent {self.unique_id}, hooray location: {self.current_edge} speed: {self.max_speed} mode: {self.decision_making_mode}\n')

    def update_state(self, water_matrix: np.ndarray):
        pass

    def step(self):
        """
        Manages agent behavior at the next step of simulation depending on its state.
        """
        if self.state == CitizenState.CRITICALLY_UNSAFE or self.state == CitizenState.RESCUED:
            return
        if self.current_edge[0] in self.model.safety_spot:
            self.state = CitizenState.RESCUED
            return
        if self.current_edge[1] is None:
            self.choose_destination()
        water_depth = self.model.space.G.nodes[self.current_edge[0]].get("depth", 0)
        if water_depth > 0.5:
            self.state = CitizenState.CRITICALLY_UNSAFE
            return
        else:
            self.current_speed = self.max_speed * np.exp(-2 * water_depth)
            self.current_speed = max(self.current_speed, 0.5)
        self.evacuate()

    def choose_destination(self):
        """
            Redirects choosing the next node to the function corresponding to the  self.decision_making_mode of the agent
        """
        current_node = self.current_edge[0]
        if self.decision_making_mode == CitizenDecisionMakingMode.RANDOM:
            self.random_path_choice(current_node)
        elif self.decision_making_mode == CitizenDecisionMakingMode.DIJIKSTRA:
            self.dijikstra_path_choice(current_node)
        elif self.decision_making_mode == CitizenDecisionMakingMode.FOLLOWER:
            self.follower_path_choice(current_node);


    def random_path_choice(self, current_node):
        """
        Chooses the next node at random

        :param current_node: The node the agent is currently at.
        """
        next_node = random.choice(list(self.model.space.get_neighborhood(current_node)))
        self.current_edge = (current_node, next_node)
        self.progress = 0.0

    def dijikstra_path_choice(self, current_node):
        """
        Runs a dijikstra algorithm to determinate the closest located safety spot and sets is as next_node in self.current_edge
        If there are no reachable_targets, assigns self.decision_making_mode to RANDOM.

        :param current_node: The node the agent is currently at.
        """
        safety_spots = self.model.safety_spot
        dist, paths = nx.single_source_dijkstra(self.model.space.G, current_node, weight="length")
        reachable_targets = [(s, dist[s], paths[s]) for s in safety_spots if s in dist]

        if not reachable_targets:
            self.decision_making_mode = CitizenDecisionMakingMode.RANDOM
            # self.decision_making_mode = CitizenDecisionMakingMode.FOLLOWER
        else:
            _, _, path = min(reachable_targets, key=lambda x: x[1])
            self.current_edge = (current_node, path[1])
    
    def follower_path_choice(self, current_node):
        """
        Copies the end node of any agent found on the same edge.
        If there're none agents with the same start node, picks path at random.
        """
        for agent in self.model.agents:
            if agent.current_edge[0] == current_node:
                self.current_edge = (current_node, agent.current_edge[1])
                break
        if self.current_edge[1] is None:
            neighbors = list(self.model.space.G.neighbors(current_node))
            self.current_edge = (current_node, random.choice(neighbors))

    def evacuate(self):
        """
        Calculates progress of the agent on the current path, moves the agent and updates current_edge.
        """
        edge_length = self.model.space.G[self.current_edge[0]][self.current_edge[1]]['length']
        self.progress += self.current_speed / edge_length

        if self.progress >= 1.0:
            # Dotarł do następnego węzła
            self.current_edge = (self.current_edge[1], None)
            self.progress = 0.0
            self.model.space.move_agent(self, self.current_edge[0])
