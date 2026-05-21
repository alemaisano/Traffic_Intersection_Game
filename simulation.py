from config import DT, HORIZON
from maps import MAPS
from network import Network
from signals import NetworkSignals
from demand import generate_od_matrix, generate_trips, od_summary
from metrics import compute_metrics
from vehicles import PENDING, ACTIVE, DONE


class SimulationEngine:
    """Deterministic timestep loop (DT = 0.1 s, horizon = 60 s)."""

    def __init__(self, map_name='downtown', scenario='balanced', seed=None):
        map_def = MAPS[map_name]

        self.network = Network(map_def)
        self.network.precompute_routes()

        self.signals = NetworkSignals(
            intersection_ids=list(map_def['intersection_nodes']),
            signal_config=map_def.get('signal_config', {}),
        )

        self.od_matrix = generate_od_matrix(
            boundary_zones=map_def['boundary_zones'],
            scenario=scenario,
            seed=seed,
        )
        self.od_info  = od_summary(self.od_matrix, map_def['boundary_zones'])
        self.vehicles = generate_trips(self.od_matrix, self.network, seed=seed)

        self.sim_time   = 0.0
        self.step_count = 0
        self.done       = False
        self.metrics    = None

    # ------------------------------------------------------------------
    def step(self):
        if self.done:
            return
        dt = DT

        # Activate pending vehicles when their departure time arrives
        for v in self.vehicles:
            if v.state == PENDING and v.depart_time <= self.sim_time:
                seg = self.network.segments.get(v.route[0]) if v.route else None
                if seg is None:
                    continue
                # Only activate if there is physical room at the back of the entry segment
                if seg.vehicles:
                    last = seg.vehicles[-1]
                    if last.rear_dist < v.length + 1.0:
                        continue
                v.activate(self.sim_time)

        # Advance signals
        self.signals.step(dt)

        # Advance vehicles — process front-to-back per segment
        for seg in self.network.segments.values():
            for v in list(seg.vehicles):
                v.step(dt, self.signals, self.sim_time)
            # Keep list sorted: index 0 = highest dist_on_seg (front)
            seg.vehicles.sort(key=lambda v: v.dist_on_seg, reverse=True)

        self.sim_time   += dt
        self.step_count += 1

        active_or_pending = any(v.state in (PENDING, ACTIVE) for v in self.vehicles)
        if self.sim_time >= HORIZON or not active_or_pending:
            self.done    = True
            self.metrics = compute_metrics(self.vehicles, self.network)

    # ------------------------------------------------------------------
    def active_vehicles(self):
        return [v for v in self.vehicles if v.state == ACTIVE]

    def counts(self):
        n_p = sum(1 for v in self.vehicles if v.state == PENDING)
        n_a = sum(1 for v in self.vehicles if v.state == ACTIVE)
        n_d = sum(1 for v in self.vehicles if v.state == DONE)
        return {'total': len(self.vehicles), 'pending': n_p, 'active': n_a, 'done': n_d}
