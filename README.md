# Serious Game for Adaptive Traffic Control

A deterministic traffic simulation turned into a serious game, built in Python with Pygame by adapting an existing simplified simulation framework (see forked project). Players take control of real traffic signals across several urban network layouts and compete for the best throughput, equity, and average delay scores.

---

## What it does

The simulation runs a 3-minute (180 s) episode on a chosen road network. Vehicles are generated from a stochastic origin–destination matrix and routed through the network by shortest path. Each signalised intersection runs a standard 2-phase (NS / EW) fixed-time controller by default. The player's job is to override those phases in real time, pushing bottlenecked intersections green, to improve traffic flow.

At the end of each run the game saves the results and shows three boxplot comparisons against all previous runs on the same map + scenario, so the player can immediately see where they rank.

---

## Features

| Feature | Detail |
|---|---|
| **6 road networks** | Boulevard (2), Main Street (3), L-Junction (3), T-Cross (4), Downtown Grid (4), City Grid (6 intersections) |
| **3 demand levels** | Light (λ = 2), Balanced (λ = 4.5), Peak (λ = 9) vehicles/minute |
| **Real-time signal control** | Click or press 1–6 to select an intersection; press **N** or **E** to force NS / EW green |
| **Simulation speed control** | **+** / **−** keys cycle through 0.25×, 0.5×, 1×, 2×, … 10× real-time; **P** to pause |
| **Performance metrics** | Throughput (%), average delay (s), equity (Jain's fairness index) |
| **Leaderboard** | All runs persisted in `scores.json`; boxplots show percentile rank against past runs |
| **Congestion snapshot** | Results screen shows how many seconds each intersection spent as a bottleneck, queued, or clear |

---

## Prerequisites

- Python 3.9+
- Pygame 2.x

```sh
pip install pygame
```

---

## Running

```sh
python main.py
```

---

## Controls

| Key / Action | Effect |
|---|---|
| Click intersection | Select it (yellow highlight) |
| **1 – 6** | Select intersection by index |
| **Tab** | Cycle to next intersection |
| **N** | Force selected intersection to NS green |
| **E** | Force selected intersection to EW green |
| **+** / **=** | Speed up simulation |
| **−** | Slow down simulation |
| **Space** | Pause / resume |
| **Esc** | Return to menu |

---

## Module overview

| File | Responsibility |
|---|---|
| `main.py` | Entry point — calls `ui.run()` |
| `ui.py` | All Pygame screens: PreRun, Running, Results |
| `config.py` | Global constants (timing, colours, vehicle params, demand lambdas) |
| `maps.py` | Road network topology definitions (6 maps) |
| `network.py` | Graph, directed segments, shortest-path routing |
| `signals.py` | `IntersectionSignal` (2-phase FSM) + `NetworkSignals` container |
| `simulation.py` | Deterministic timestep loop; accumulates per-intersection congestion stats |
| `vehicles.py` | `Vehicle` class — kinematics, car-following, segment advance |
| `demand.py` | Stochastic OD matrix + trip generation (Poisson via Binomial) |
| `metrics.py` | Throughput, average delay, Jain equity index |
| `scores.py` | JSON persistence, Pareto-front helpers, percentile-rank queries |

---

## Scoring

Three metrics are reported at the end of each run and plotted against all previous runs on the same map + scenario:

- **Throughput** — share of generated vehicles that completed their trip (0–100 %).
- **Equity** — Jain's fairness index over individual trip delays (0–100 %). Higher = fairer distribution.
- **Average delay** — mean extra travel time per completed vehicle (seconds). Lower is better.

Scores are stored in `scores.json` and accumulate across sessions (up to 300 runs per map + scenario combination).

---

## License

No license yet. Please contact the authors (Alessandro Maisano + Fei Fan) for any question or issue!
