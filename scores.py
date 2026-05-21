"""
scores.py  –  Persistent leaderboard and Pareto-front helpers.

Scores are stored in scores.json next to the game.
Key format: "{map_name}_{scenario}"  e.g. "downtown_balanced"
Objectives: maximise throughput, minimise avg_delay.
"""

import json
import os
from datetime import date

SCORES_FILE = 'scores.json'
MAX_RUNS_PER_KEY = 300


def load_scores():
    if not os.path.exists(SCORES_FILE):
        return {}
    try:
        with open(SCORES_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_run(map_name, scenario, metrics):
    """Append current run, persist, return the full list for this key."""
    scores = load_scores()
    key    = f'{map_name}_{scenario}'
    entry  = {
        'throughput': round(metrics['throughput'], 4),
        'avg_delay':  round(metrics['avg_delay'],  2),
        'equity':     round(metrics['equity'],      4),
        'completed':  metrics['completed'],
        'total':      metrics['total'],
        'date':       str(date.today()),
    }
    bucket = scores.get(key, [])
    bucket.append(entry)
    bucket = bucket[-MAX_RUNS_PER_KEY:]
    scores[key] = bucket
    try:
        with open(SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(scores, f)
    except Exception:
        pass
    return bucket


def pareto_indices(runs):
    """
    Return indices of Pareto-optimal runs.
    A run is optimal if no other run is at least as good on BOTH axes
    and strictly better on at least one (higher throughput OR lower delay).
    """
    n = len(runs)
    dominated = [False] * n
    for i in range(n):
        if dominated[i]:
            continue
        for j in range(n):
            if i == j or dominated[j]:
                continue
            j_tp = runs[j]['throughput']
            j_dl = runs[j]['avg_delay']
            i_tp = runs[i]['throughput']
            i_dl = runs[i]['avg_delay']
            if (j_tp >= i_tp and j_dl <= i_dl and
                    (j_tp > i_tp or j_dl < i_dl)):
                dominated[i] = True
                break
    return [i for i in range(n) if not dominated[i]]
