import random
from config import BOUNDARY_ZONES, VEHICLE_MIX, SCENARIOS, HORIZON
from vehicles import Vehicle, reset_id_counter


def generate_od_matrix(scenario: str = 'balanced', seed=None) -> dict:
    """Return OD dict {(origin, dest): count}  using Poisson-like demand."""
    rng = random.Random(seed)
    lam = SCENARIOS[scenario]['lam']
    matrix = {}
    for o in BOUNDARY_ZONES:
        for d in BOUNDARY_ZONES:
            if o == d:
                matrix[(o, d)] = 0
            else:
                # Poisson approximation: sum of Bernoulli trials
                # Use at least 10 trials; p = lam/trials keeps E[X]=lam
                trials = max(10, int(lam * 4))
                p      = lam / trials
                matrix[(o, d)] = sum(1 for _ in range(trials) if rng.random() < p)
    return matrix


def od_summary(matrix: dict) -> dict:
    """Aggregate totals useful for the pre-run display."""
    total = sum(matrix.values())
    by_origin = {}
    for (o, d), cnt in matrix.items():
        by_origin[o] = by_origin.get(o, 0) + cnt
    return {'total': total, 'by_origin': by_origin}


def sample_vehicle_class(rng: random.Random) -> str:
    r = rng.random()
    cum = 0.0
    for vc, prob in VEHICLE_MIX:
        cum += prob
        if r < cum:
            return vc
    return 'car'


def generate_trips(od_matrix: dict, network, horizon: float = HORIZON, seed=None) -> list:
    """Create Vehicle objects (state=PENDING) for every OD demand unit."""
    reset_id_counter()
    rng  = random.Random(seed)
    trips = []
    for (origin, dest), count in od_matrix.items():
        if count == 0:
            continue
        route = network.get_route(origin, dest)
        if route is None:
            continue
        for _ in range(count):
            vclass     = sample_vehicle_class(rng)
            depart     = rng.uniform(0.0, horizon * 0.75)
            v          = Vehicle(vclass, route, network, depart)
            v.origin_zone = origin
            v.dest_zone   = dest
            trips.append(v)
    trips.sort(key=lambda v: v.depart_time)
    return trips
