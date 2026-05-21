import math
from vehicles import DONE


def compute_metrics(vehicles, network):
    total     = len(vehicles)
    completed = [v for v in vehicles if v.state == DONE]
    n_done    = len(completed)
    throughput = n_done / total if total > 0 else 0.0

    od_delays = {}
    for v in completed:
        ff    = network.free_flow_time(v.route, v.vclass)
        actual = v.actual_arrive - v.actual_depart
        v.delay = max(0.0, actual - ff)
        key   = (v.origin_zone, v.dest_zone)
        od_delays.setdefault(key, []).append(v.delay)

    all_delays = [d for ds in od_delays.values() for d in ds]
    avg_delay  = sum(all_delays) / len(all_delays) if all_delays else 0.0

    # Equity: 1 - coefficient of variation of per-OD mean delay
    od_means = [sum(ds) / len(ds) for ds in od_delays.values() if ds]
    if len(od_means) >= 2:
        mu  = sum(od_means) / len(od_means)
        std = math.sqrt(sum((m - mu) ** 2 for m in od_means) / len(od_means))
        equity = max(0.0, 1.0 - std / (mu + 1e-6))
    elif len(od_means) == 1:
        equity = 1.0
    else:
        equity = 0.0

    w_done  = sum(v.weight for v in completed)
    w_total = sum(v.weight for v in vehicles)
    weighted_throughput = w_done / w_total if w_total > 0 else 0.0

    # Per-intersection residual queue
    queue_stats = {}
    for iid in network.intersection_nodes:
        queue_stats[iid] = sum(
            len(seg.vehicles)
            for seg in network.segments.values()
            if seg.enters_intersection == iid
        )

    bottleneck = max(queue_stats, key=queue_stats.get) if queue_stats else None

    return {
        'total':               total,
        'completed':           n_done,
        'throughput':          throughput,
        'weighted_throughput': weighted_throughput,
        'avg_delay':           avg_delay,
        'equity':              equity,
        'queue_stats':         queue_stats,
        'bottleneck':          bottleneck,
        'od_delays':           od_delays,
    }
