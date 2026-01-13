import mesa
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import networkx as nx
import random 
import os

from agent_model.citizens.citizen_agent import CitizenAgent, CitizenState
from agent_model.call_center_agent import CallCenterAgent
from agent_model.rescue_agent import RescueAgent, RescueState
from flood_agent.model.model import FloodModel

class EvacModel(mesa.Model):
    def __init__(self, n_agents, roads_graph, dem_path, flood_model: FloodModel, n_rescue=12):
        super().__init__()
        self.count = 0

        self.space = mesa.space.NetworkGrid(roads_graph) # Create a NetworkGrid based on the road graph
        self.create_rescue_agents(n=n_rescue)
        self.create_agents(n=n_agents)
        self.call_center = CallCenterAgent(self)
        self.safety_spot = [n for n, d in self.space.G.nodes(data=True) if d.get("is_safe_spot")] # Example of a safe spot node

        self.flood_model = flood_model
        if flood_model is not None:
            self.height = flood_model.area
            self.water = flood_model.water

        self.visual_data = {
            "agent_positions": [],  # lista słowników: {agent_id: (x, y), ...}
            "rescue_positions": [],
            "water": [],
        }

        self.stats = {
            "safety_arrival_times": [], # czasy dotarcia do bezpiecznego miejsca
            "rescue_response_time": [], # listy czasów reakcji ratowników
            "rescue_to_safety_time": [], # listy czasów od ratunku do bezpieczeństwa

            "safe_count": [],          # liczba osób bezpiecznych w danym kroku
            "rescued_count": [],        # liczba osób uratowanych w danym kroku
            "critically_unsafe_count": [],  # liczba ludzi w stanie krytycznym
            "unsafe_count": [],          # liczba ludzi w stanie niebezpiecznym
            "available_rescuers": [],   # liczba dostępnych ratowników
            "on_mission_rescuers": [],  # liczba ratowników w misji
            "carrying_rescuers": [],     # liczba ratowników transportujących poszkodowanych
            "unsafe_edges": [],         # liczba zalanych krawędzi w grafie
        }

    
    def create_rescue_agents(self, n: int):
        spawn_points = [n for n, d in self.space.G.nodes(data=True) if d.get("is_rescue_base")]
        i = 0
        for node in spawn_points:
            for _ in range(3):
                agent = RescueAgent(self, start_node=node)
                self.agents.add(agent)
                self.space.place_agent(agent, node)
            i += 3
            if i >= n:
                break
    
    def create_agents(self, n: int):
        valid_nodes = [node for node, data in self.space.G.nodes(data=True) if 300 <= data['pos_array'][1] <= 1000 
                       and (0 <= data['pos_array'][0] <= 600 or 1700 <= data['pos_array'][0] <= 2100)]
        for i in range(n//2):
            start_node = random.choice(valid_nodes)
            agent = CitizenAgent(self, start_node=start_node)
            self.agents.add(agent)
            self.space.place_agent(agent, start_node)

            start_node = random.choice(list(self.space.G.nodes))
            agent = CitizenAgent(self, start_node=start_node)
            self.agents.add(agent)
            self.space.place_agent(agent, start_node)

    
    def flood_step(self):
        """
        Update flood simulation and map depth values to the road network.
        """
        # --- Flood update ---
        self.flood_model.step(1)
        self.water = self.flood_model.water

        for n, data in self.space.G.nodes(data=True):
            col, row = data['pos_array']
            try:
                depth = float(self.water[row, col])
                data["depth"] = depth
            except IndexError:
                data["depth"] = 0.0

        # --- Mark unsafe roads ---
        for u, v, d in self.space.G.edges(data=True):
            node_depth = max(
                self.space.G.nodes[u].get("depth", 0),
                self.space.G.nodes[v].get("depth", 0),
            )
            d["safe"] = "no" if node_depth > 0.5 else "yes"  
        
    def step(self):
        if self.count%10 == 0:
            if self.flood_model is not None:
                self.flood_step() # Update water depth on graph nodes

        if self.count%20 == 0 and self.count > 0:    
            self.create_agents(100)
                   

        if self.count%5 == 0:
            self.call_center.step()

        
        self.agents.do("step")
        self.visualise_step()
        
        self.count += 1

        self.stats["safe_count"].append(len([a for a in self.agents if isinstance(a, CitizenAgent) and a.state == CitizenState.SAFE]))
        self.stats["rescued_count"].append(len([a for a in self.agents if isinstance(a, CitizenAgent) and a.state == CitizenState.RESCUED]))
        self.stats["critically_unsafe_count"].append(len([a for a in self.agents if isinstance(a, CitizenAgent) and a.state == CitizenState.CRITICALLY_UNSAFE]))
        self.stats["unsafe_count"].append(len([a for a in self.agents if isinstance(a, CitizenAgent) and a.state == CitizenState.UNSAFE]))
        self.stats["available_rescuers"].append(len([a for a in self.agents if isinstance(a, RescueAgent) and a.state == RescueState.AVAILABLE]))
        self.stats["on_mission_rescuers"].append(len([a for a in self.agents if isinstance(a, RescueAgent) and a.state == RescueState.ON_MISSION]))
        self.stats["carrying_rescuers"].append(len([a for a in self.agents if isinstance(a, RescueAgent) and a.state == RescueState.CARRYING]))
        self.stats["unsafe_edges"].append(len([e for e in self.space.G.edges(data=True) if e[2].get("safe") == "no"]))


    def visualise_step(self):
        agent_positions = {}
        rescue_positions = {}
        pos = nx.get_node_attributes(self.space.G, "pos_array")

        agents = [a for a in self.agents if isinstance(a, RescueAgent) or (isinstance(a, CitizenAgent) and a.state != CitizenState.SAFE)]
        for agent in agents:
            if not isinstance(agent, (CitizenAgent, RescueAgent)):
                continue
            x0, y0 = pos[agent.current_edge[0]]
            if agent.current_edge[1] is not None:
                x1, y1 = pos[agent.current_edge[1]]
                x = x0 + (x1 - x0) * agent.progress
                y = y0 + (y1 - y0) * agent.progress
            else:
                x, y = x0, y0
            if isinstance(agent, RescueAgent):
                rescue_positions[agent.unique_id] = (x, y)
            if isinstance(agent, CitizenAgent):
                if agent.state != CitizenState.SAFE:
                    agent_positions[agent.unique_id] = (x, y)

        self.visual_data["agent_positions"].append(agent_positions)
        self.visual_data["rescue_positions"].append(rescue_positions)
        if self.flood_model is not None:
            self.visual_data["water"].append(self.water.copy())


from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation, FFMpegWriter
def animate_simulation(model:EvacModel, save_path="evacuation_simulation.mp4", fps=5):
    G = model.space.G
    pos = nx.get_node_attributes(G, "pos_array")
    safety_spot = model.safety_spot

    fig2, ax = plt.subplots(figsize=(10,5))
    def update(frame):
        ax.clear()
        if model.flood_model is not None:
            ax.imshow(model.flood_model.area, cmap='terrain', 
                      vmin=model.flood_model.global_min, vmax=model.flood_model.global_max)
            water = model.visual_data["water"][frame]
            water_mask = np.where(water > 0.1, water, np.nan)
            ax.imshow(water_mask, cmap='Blues', alpha=0.6, vmin=-0.5, vmax=1.0)
            ax.imshow(np.where(model.flood_model.river_mask == True, model.flood_model.river_mask, np.nan), cmap="Blues", alpha=0.7, vmin=-0.5, vmax=1.0)
            
        
        # rysuj sieć dróg
        safe_edges = [(u,v,d) for u,v,d in G.edges(data=True) if d.get('safe')=='yes']
        unsafe_edges = [(u,v,d) for u,v,d in G.edges(data=True) if d.get('safe')=='no']
        nx.draw_networkx_edges(G, pos, edgelist=[(u,v) for u,v,_ in safe_edges], edge_color='black', width=0.5, ax=ax)
        nx.draw_networkx_edges(G, pos, edgelist=[(u,v) for u,v,_ in unsafe_edges], edge_color='red', width=0.5, ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=safety_spot, node_color='green', node_size=5, ax=ax)

        # rysuj agentów
        agent_positions = model.visual_data["agent_positions"][frame]
        rescue_positions = model.visual_data["rescue_positions"][frame]
        ax.scatter([p[0] for p in agent_positions.values()],
                   [p[1] for p in agent_positions.values()],
                   c="#c800cf", s=2, label='Agents', zorder=2)
        ax.scatter([p[0] for p in rescue_positions.values()],
                   [p[1] for p in rescue_positions.values()],
                   c='purple', s=5, label='Rescue Agents', zorder=2)

        ax.set_title(f"Step {frame}")
        ax.legend()
    ani = animation.FuncAnimation(fig2, update, frames=len(model.visual_data["agent_positions"]),
                                  interval=1000/fps)

    # Zapisz jako GIF
    #ani.save(save_path, writer='pillow', fps=fps)
    writer = FFMpegWriter(fps=fps, bitrate=2000)

    ani.save(save_path, writer=writer)
    plt.close(fig2)
    print(f"Animacja zapisana: {save_path}")

    '''
    fig, ax = plt.subplots(figsize=(10,10))
    plt.subplots_adjust(bottom=0.15)

    def draw_frame(frame):
        ax.clear()
        if model.flood_model is not None:
            ax.imshow(model.flood_model.area, cmap='terrain', 
                      vmin=model.flood_model.global_min, vmax=model.flood_model.global_max)
            water = model.visual_data["water"][frame]
            water_mask = np.where(water > 0.1, water, np.nan)
            ax.imshow(water_mask, cmap='Blues', alpha=0.6, vmin=-0.5, vmax=1.0)
            ax.imshow(np.where(model.flood_model.river_mask == True, model.flood_model.river_mask, np.nan), cmap="Blues", alpha=0.7, vmin=-0.5, vmax=1.0)
        
        # rysuj sieć dróg
        safe_edges = [(u,v,d) for u,v,d in G.edges(data=True) if d.get('safe')=='yes']
        unsafe_edges = [(u,v,d) for u,v,d in G.edges(data=True) if d.get('safe')=='no']
        nx.draw_networkx_edges(G, pos, edgelist=[(u,v) for u,v,_ in safe_edges], edge_color='black', width=0.5, ax=ax)
        nx.draw_networkx_edges(G, pos, edgelist=[(u,v) for u,v,_ in unsafe_edges], edge_color='red', width=0.5, ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=safety_spot, node_color='green', node_size=5, ax=ax)

        # rysuj agentów
        agent_positions = model.visual_data["agent_positions"][frame]
        rescue_positions = model.visual_data["rescue_positions"][frame]
        ax.scatter([p[0] for p in agent_positions.values()],
                   [p[1] for p in agent_positions.values()],
                   c="#c800cf", s=2, label='Agents', zorder=2)
        ax.scatter([p[0] for p in rescue_positions.values()],
                   [p[1] for p in rescue_positions.values()],
                   c='purple', s=5, label='Rescue Agents', zorder=2)

        ax.set_title(f"Step {frame}")
        ax.legend()

    n_frames = len(model.visual_data["agent_positions"])
    frame = [0]

    draw_frame(frame[0])

    # Funkcje przycisków
    def next_step(event):
        frame[0] = (frame[0] + 1) % n_frames
        draw_frame(frame[0])
        fig.canvas.draw_idle()

    def prev_step(event):
        frame[0] = (frame[0] - 1) % n_frames
        draw_frame(frame[0])
        fig.canvas.draw_idle()

    ax_next = plt.axes([0.8, 0.05, 0.1, 0.04])
    ax_prev = plt.axes([0.69, 0.05, 0.1, 0.04])
    b_next = Button(ax_next, 'Next')
    b_prev = Button(ax_prev, 'Prev')
    b_next.on_clicked(next_step)
    b_prev.on_clicked(prev_step)

    plt.show()
    '''

import pandas as pd
def save_stats_to_csv(model, folder_path):
    os.makedirs(folder_path, exist_ok=True)

    # --- 1. Zapis statystyk krokowych ---
    step_data = pd.DataFrame({
        "safe_count": model.stats["safe_count"],
        "rescued_count": model.stats["rescued_count"],
        "critically_unsafe_count": model.stats["critically_unsafe_count"],
        "unsafe_count": model.stats["unsafe_count"],
        "available_rescuers": model.stats["available_rescuers"],
        "on_mission_rescuers": model.stats["on_mission_rescuers"],
        "carrying_rescuers": model.stats["carrying_rescuers"],
        "unsafe_edges": model.stats["unsafe_edges"],
    })
    step_file = os.path.join(folder_path, "step_stats.csv")
    step_data.to_csv(step_file, index_label="step")

    # --- 2. Zapis statystyk zdarzeniowych ---
    event_stats = []

    for key in ["safety_arrival_times", "rescue_response_time", "rescue_to_safety_time"]:
        times = model.stats.get(key, [])
        if times:
            times_array = np.array(times)
            stats_dict = {
                "stat": key,
                "count": len(times_array),
                "mean": np.mean(times_array),
                "median": np.median(times_array),
                "min": np.min(times_array),
                "max": np.max(times_array),
                "std": np.std(times_array)
            }
        else:
            stats_dict = {
                "stat": key,
                "count": 0,
                "mean": np.nan,
                "median": np.nan,
                "min": np.nan,
                "max": np.nan,
                "std": np.nan
            }
        event_stats.append(stats_dict)

    event_file = os.path.join(folder_path, "event_stats.csv")
    pd.DataFrame(event_stats).to_csv(event_file, index=False)

    print(f"Step stats saved to: {step_file}")
    print(f"Event stats saved to: {event_file}")


