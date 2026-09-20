# Data policy

This repository intentionally does **not** contain the client file MapProbabilidad_adulto.csv.

The repository is public. Put the client file only in your local clone at:

data/raw/MapProbabilidad_adulto.csv

That folder is ignored by Git.

## Provenance labels

The pipeline writes outputs/audit.json and uses explicit labels:

- CLIENT_INPUT: probability grid supplied by the project/client.
- SIMULATED_DEMO: probability grid generated only for tests, CI, and demonstrations.

Vessel trajectories are always outputs of the optimization/simulation model and are not historical AIS/SISESAT tracks.
