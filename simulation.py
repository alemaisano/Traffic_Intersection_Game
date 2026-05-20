from config import DT, HORIZON
from network import Network
from signals import NetworkSignals
from demand import generate_od_matrix, generate_trips, od_summary
from metrics import compute_metrics
from vehicles import PENDING, ACTIVE, DONE


class SimulationEngine:
    """
    Deterministic timestep loop.
    Call step() once per DT (0.1 s) from the render loop.
    """

    def __init__(self, timing=None,
                 scenario: str = 'balanced', seed=None):
        self.network = Network()
        self.network.precompute_routes()

        self.signals = NetworkSignals()
        if timing:
            self.signals.apply_timing(timing)

        self.od_matrix = generate_od_matrix(scenario, seed)
        self.od_info   = od_summary(self.od_matrix)
        self.vehicles  = generate_trips(self.od_matrix, self.network, seed=seed)

        self.sim_time   = 0.0
        self.step_count = 0
        self.done       = False
        self.metrics    = None

    # ------------------------------------------------------------------
    def step(self):
        if self.done:
            return

        dt = DT

        # Activate vehicles whose departure time has been reached
        for v in self.vehicles:
            if v.state == PENDING and v.depart_time <= self.sim_time:
                seg = self.network.segments.get(v.route[0]) if v.route else None
                if seg is None:
                    continue
                # Only activate if there is room at the back of the entry segment
                if seg.vehicles:
                    last = seg.vehicles[-1]   # rear-most vehicle
                    if last.rear_dist < v.length + 1.0:
                        continue   # no room, keep pending
                v.activate(self.sim_time)

        # Advance signals
        self.signals.step(dt)

        # Advance vehicles.
        # Process each segment front-to-back so the ahead vehicle moves first.
        for seg in self.network.segments.values():
            for v in list(seg.vehicles):   # copy: list may change during advance
                v.step(dt, self.signals, self.sim_time)
            # Re-sort by dist_on_seg descending (front first) to keep ordering valid
            seg.vehicles.sort(key=lambda v: v.dist_on_seg, reverse=True)

        self.sim_time   += dt
        self.step_count += 1

        # Termination
        active_or_pending = any(v.state in (PENDING, ACTIVE) for v in self.vehicles)
        if self.sim_time >= HORIZON or not active_or_pending:
            self.done    = True
            self.metrics = compute_metrics(self.vehicles, self.network)

    # ------------------------------------------------------------------
    def active_vehicles(self) -> list:
        return [v for v in self.vehicles if v.state == ACTIVE]

    def counts(self) -> dict:
        n_pending   = sum(1 for v in self.vehicles if v.state == PENDING)
        n_active    = sum(1 for v in self.vehicles if v.state == ACTIVE)
        n_done      = sum(1 for v in self.vehicles if v.state == DONE)
        return {'total': len(self.vehicles),
                'pending': n_pending, 'active': n_active, 'done': n_done}
