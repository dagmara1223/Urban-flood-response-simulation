import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

folder = "output/standard5"
title = "standard"
event_stats = pd.read_csv(f"{folder}/event_stats.csv")
step_stats = pd.read_csv(f"{folder}/step_stats.csv")

pop_cols = [
    "safe_count",
    "rescued_count",
    "critically_unsafe_count",
    "unsafe_count"
]

expected_total = step_stats[pop_cols].iloc[-1].sum()
for idx, row in step_stats.iterrows():
    current_total = row[pop_cols].sum()
    diff = expected_total - current_total

    if diff != 0:
        step_stats.loc[idx, "safe_count"] += diff


event_keys = ["safety_arrival_times", "rescue_response_time", "rescue_to_safety_time"]

print("\nEVENT STATS SUMMARYn")

for key in event_keys:
    if key not in event_stats["stat"].values:
        print(f"Brak danych dla {key}")
        continue

    row = event_stats[event_stats["stat"] == key].iloc[0]
    print(f"--- {key} ---")
    print(f"count:  {row['count']}")
    print(f"mean:   {row['mean']:.2f}")
    print(f"median: {row['median']:.2f}")
    print(f"min:    {row['min']}")
    print(f"max:    {row['max']}")
    print(f"std:    {row['std']:.2f}\n")


# STEP STATS
plt.figure(figsize=(12,6))
for col in ["safe_count", "rescued_count", "critically_unsafe_count", "unsafe_count"]:
    plt.plot(step_stats["step"], step_stats[col], label=col)
plt.legend()
plt.title(f"Population states over simulation time - {title}")
plt.xlabel("Step")
plt.ylabel("Count")
plt.savefig(f"{folder}/population_state.png")
plt.show()


plt.figure(figsize=(12,6))
for col in ["available_rescuers", "on_mission_rescuers", "carrying_rescuers"]:
    plt.plot(step_stats["step"], step_stats[col]*4, label=col)
plt.legend()
plt.title(f"Rescuer activity over time - {title}")
plt.xlabel("Step")
plt.ylabel("Count")
plt.savefig(f"{folder}/rescuers_state.png")
plt.show()

plt.figure(figsize=(10,5))
plt.plot(step_stats["step"], step_stats["unsafe_edges"], color="red")
plt.title(f"Unsafe road edges over time - {title}")
plt.xlabel("Step")
plt.ylabel("Unsafe edges")
plt.savefig(f"{folder}/unsafe_roads.png")
plt.show()


# CORRELATION MATRIX
plt.figure(figsize=(10,8))
sns.heatmap(step_stats.drop(columns=["step"]).corr(), annot=True, fmt=".2f", cmap="coolwarm")
plt.title(f"Correlation matrix among step statistics - {title}")
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig(f"{folder}/correlation_matrix.png")
plt.show()
