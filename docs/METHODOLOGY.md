# Methodology and evidence boundary

## Core problem

The project assigns 15 homogeneous anchoveta purse-seiner agents to spatial candidate zones while balancing probability of presence and travel/fuel cost.

## What is observed / supplied

- The client probability grid, when present locally.
- Publicly documented reference port locations used by the academic model.

## What is modeled

- Candidate-zone selection.
- A* routes through valid grid cells.
- Greedy and MILP fleet allocation.
- Animated vessel movement along planned routes.

## What is simulated

- All vessel movements in maps/GIFs are simulated model outputs.
- When --demo is used, the probability field is also simulated and is labeled SIMULATED_DEMO.

## What is not claimed

- The simulated routes are not historical vessel tracks.
- Probability of presence is not interpreted as catch tonnage.
- Reference fuel and vessel parameters are scenario parameters, not telemetry from the client's fleet.

## External-data strategy

The robust core intentionally runs without fragile external APIs. Official environmental layers can be added later as optional modules, but the core pipeline remains executable and auditable without them.
