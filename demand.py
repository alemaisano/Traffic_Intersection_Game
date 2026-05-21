import random
from config import VEHICLE_MIX, SCENARIOS, HORIZON
from vehicles import Vehicle, reset_id_counter


def generate_od_matrix(boundary_zones, scenario='balanced', seed=None):
    """Return {(origin, dest): count} using Poisson-like demand."""
    rng  = random.Random(seed)
    lam  = SCENARIOS[scenario]['lam']
    trials = max(10, int(lam * 4))
    p      = lam / trials
    matrix = {}
    for o in boundary_zones:
        for d in boundary_zones:
            if o == d:
                matrix[(o, d)] = 0
            else:
                matrix[(o, d)] = sum(1 for _ in range(trials) if rng.random() < p)
    return matrix


def od_summary(matrix, boundary_zones):
    total      = sum(matrix.values())
    by_origin  = {z: 0 for z in boundary_zones}
    for (o, d), cnt in matrix.items():
        by_origin[o] = by_origin.get(o, 0) + cnt
    return {'total': total, 'by_origin': by_origin}


def _sample_vehicle_class(rng):
    r = rng.random()
    cum = 0.0
    for vc, prob in VEHICLE_MIX:
        cum += prob
        if r < cum:
            return vc
    return VEHICLE_MIX[0][0]


def generate_trips(od_matrix, network, horizon=HORIZON, seed=None):
    """Create Vehicle objects (state=PENDING) for every demand unit."""
    reset_id_counter()
    rng   = random.Random(seed)
    trips = []
    for (origin, dest), count in od_matrix.items():
        if count == 0:
            continue
        route = network.get_route(origin, dest)
        if route is None:
            continue
        for _ in range(count):
            vclass    = _sample_vehicle_class(rng)
            depart    = rng.uniform(0.0, horizon * 0.75)
            v         = Vehicle(vclass, route, network, depart)
            v.origin_zone = origin
            v.dest_zone   = dest
            trips.append(v)
    trips.sort(key=lambda v: v.depart_time)
    return trips
