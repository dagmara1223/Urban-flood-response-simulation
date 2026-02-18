# 🌊 Urban Flood Response Simulation – Kraków 2010   
Hybrid flood and evacuation simulation combining a raster-based hydrological model with an agent-based evacuation model.
The project simulates urban flooding and human behavior during crisis situations using realistic terrain, rainfall scenarios, and road networks.

## Overview  
This project models a historical flood scenario inspired by the 2010 flood in Kraków and studies:  
- How flood water propagates in urban terrain,  
- How citizens react to increasing danger,  
- How rescue services impact evacuation efficiency,   
- How different strategies influence survival and evacuation time.  
<br>
The system integrates: <br>  
🌊 hydrodynamic surface water model   <br>
🤖 agent-based evacuation model  <br>
🗺️ real DEM terrain data  <br>
🛣️ real road network graph  <br>
💦 scenario-based rainfall simulation   <br>
🔦 rescue logistics and mission assignment <br>

# Core Concepts   
## Flood Model    
A raster-based surface flow model inspired by storage-cell and diffusion approaches: <br>
- DEM-based terrain representation <br>
- 8-direction (Moore neighborhood) flow <br>
- rainfall time blocks <br>
- terrain-dependent retention <br>
- increased flow along roads <br>
- levee overflow mechanism <br>
- flow regulation via empirical coefficient <br>
<br>
Each grid cell stores: <br>
- terrain height <br>
- water height <br>
- total water level <br>
<br>
Water flows only toward lower total levels. <br>


## Agent-Based Evacuation Model   
Implemented with Mesa-style agents and road graph navigation.  <br>  
### Citizens   
Each citizen has: <br>
- randomized walking speed <br>
- dynamic speed reduction in water <br> 
- safety state:     
-- SAFE <br>
-- UNSAFE <br> 
-- CRITICALLY_UNSAFE <br>
-- RESCUED <br>  
- decision strategy:    
-- DIJKSTRA (optimal path)      
-- RANDOM (panic mode)      
-- FOLLOWER (social behavior)    
### Rescure Agents  
Rescuers:    
- are assigned dynamically to critical citizens <br>
- can transport victims to safe zones <br>
- operate in states:   
-- AVAILABLE     
-- ON_MISSION     
-- CARRYING        

Mission assignment is distance-based and availability-aware.  

# Simulation   
## Step 0 <br>
<img width="700" height="493" alt="image" src="https://github.com/user-attachments/assets/2a8ecd6d-165c-4df2-976b-bc74ccf4be8f" /> <br> 
## Step 63 <br>
<img width="700" height="486" alt="image" src="https://github.com/user-attachments/assets/e8d6c4d7-9bdb-4258-9e08-8fc5dcc3d296" /> <br>
## Step 147 <br>
<img width="700" height="494" alt="image" src="https://github.com/user-attachments/assets/d5dcd71f-0b89-40c2-a226-b31ce155bdd7" /> <br>
## Step 380 <br> 
<img width="700" height="483" alt="image" src="https://github.com/user-attachments/assets/c71eefc9-0472-4c14-b8fb-1e4358f587b7" /> <br>
## Step 594 <br> 
<img width="700" height="493" alt="image" src="https://github.com/user-attachments/assets/3649263f-7b0f-4713-92b9-ffa2684648ef" /> <br>  

## Results  
<img width="700" height="600" alt="image" src="https://github.com/user-attachments/assets/ea1cbc80-d4cb-4f18-9572-7bc4addf7acb" /> <br>

Following events:  
- Decrease in the number of people that are safe -- SAFE_COUNT         
-  Constant increase in the number of people at risk -- UNSAFE_COUNT      
- Moderate increase in rescued people -- RESCUED_COUNT     
- Small increase of people at critical risk -- CRITICALLY_UNSAFE
  
## 📁 Project Structure (simplified)
```
Urban-flood-response-simulation/
│
├── Data/
│   ├── create_graph.py
|   ├── create_graph_water.py       
│   └── krakow_roads_all_2.graphml    
│
├── agent_model/
│   ├── citizens/               
│   ├── call_center_agent.py    
│   ├── model_description.md           
│   └── rescue_agent.py        
│
├── flood-agent/                  
│   ├── model/                  
│   └── output/
│   └── validation/                              

```

## Running the Simulation  ➡️  
# Requirements  
- Python 3.10+
- Libraries: <br>
```
numpy 
matplotlib 
networkx 
mesa 
rasterio 
geopandas
shapely 
scipy
osmnx 
```

- Install:  <br>
```
conda env create -f environment.yml
```

- Activate: <br>
```bash
conda activate flood-simulation
```

- Run: <br>
```
python main.py
```

- You can also run a selected scenario and number of steps: <br>
```bash
python main.py <scenario> <number_of_steps>
```

- You can enable/disable:<br>
```
run_flood_simulation = True    
run_evacuation_simulation = True    
run_validation = False
```

## 📊 Outputs in a nutshell   
The simulation produces: <br>
- evacuation statistics (CSV)
- time-series population states
- rescue activity metrics
- dangerous road segments analysis
- flood maps
- MP4 animations
<br>



