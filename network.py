import math
import heapq
from config import (NODE_PIXELS, INTERSECTION_NODES, BOUNDARY_ZONES, ROAD_PAIRS,
                    PIXELS_PER_METER, LANE_OFFSET_PX, INTERSECTION_HALF_M,
                    INTERSECTION_HALF_PX, VEHICLE_PARAMS)


def _direction(from_name, to_name):
    fx, fy = NODE_PIXELS[from_name]
    tx, ty = NODE_PIXELS[to_name]
    dx, dy = tx - fx, ty - fy
    if abs(dx) >= abs(dy):
        return 'E' if dx > 0 else 'W'
    return 'S' if dy > 0 else 'N'


def _pixel_dist(a, b):
    ax, ay = NODE_PIXELS[a]
    bx, by = NODE_PIXELS[b]
    return math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)


def _lane_endpoints(from_name, to_name):
    """Centre-of-lane pixels for the directed segment from_name → to_name."""
    fx, fy = NODE_PIXELS[from_name]
    tx, ty = NODE_PIXELS[to_name]
    dx, dy = tx - fx, ty - fy
    dist = math.sqrt(dx * dx + dy * dy)
    ux, uy = dx / dist, dy / dist
    # Right perpendicular (right-hand traffic)
    rx, ry = uy, -ux
    ox, oy = rx * LANE_OFFSET_PX, ry * LANE_OFFSET_PX
    return (fx + ox, fy + oy), (tx + ox, ty + oy)


class Segment:
    """One directed road segment between two network nodes."""

    __slots__ = ('id', 'from_node', 'to_node', 'direction', 'length_m',
                 'px_start', 'px_end', 'enters_intersection', 'stop_line_m',
                 'vehicles')

    def __init__(self, seg_id, from_node, to_node):
        self.id = seg_id
        self.from_node = from_node
        self.to_node = to_node
        self.direction = _direction(from_node, to_node)
        px_len = _pixel_dist(from_node, to_node)
        self.length_m = px_len / PIXELS_PER_METER
        self.px_start, self.px_end = _lane_endpoints(from_node, to_node)
        self.enters_intersection = to_node if to_node in INTERSECTION_NODES else None
        self.stop_line_m = (self.length_m - INTERSECTION_HALF_M
                            if self.enters_intersection else self.length_m)
        self.vehicles: list = []   # ordered: index 0 = closest to segment end (front)

    def pixel_at(self, dist_m: float):
        """Screen pixel for the front of a vehicle at dist_m along this segment."""
        t = max(0.0, min(1.0, dist_m / self.length_m))
        sx, sy = self.px_start
        ex, ey = self.px_end
        return (sx + (ex - sx) * t, sy + (ey - sy) * t)

    def stop_line_pixel(self):
        return self.pixel_at(self.stop_line_m)

    def free_flow_time(self, vclass: str) -> float:
        return self.length_m / VEHICLE_PARAMS[vclass]['max_speed']


class Network:
    def __init__(self):
        self.segments = {}
        self.adj = {}   # from_node -> [(to_node, seg_id, length_m)]
        self._build()
        self._routes: dict = {}

    def _build(self):
        for (a, b) in ROAD_PAIRS:
            for frm, to in ((a, b), (b, a)):
                sid = f"{frm}->{to}"
                seg = Segment(sid, frm, to)
                self.segments[sid] = seg
                self.adj.setdefault(frm, []).append((to, sid, seg.length_m))

    # ------------------------------------------------------------------
    def shortest_path(self, origin: str, dest: str):
        """Dijkstra. Returns list of seg_ids or None if unreachable."""
        dist = {n: float('inf') for n in NODE_PIXELS}
        prev = {n: None for n in NODE_PIXELS}
        dist[origin] = 0.0
        pq = [(0.0, origin)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == dest:
                break
            for v, sid, w in self.adj.get(u, []):
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = (u, sid)
                    heapq.heappush(pq, (nd, v))
        path, cur = [], dest
        while prev[cur] is not None:
            u, sid = prev[cur]
            path.append(sid)
            cur = u
        path.reverse()
        return path if path else None

    def precompute_routes(self):
        for o in BOUNDARY_ZONES:
            for d in BOUNDARY_ZONES:
                if o != d:
                    self._routes[(o, d)] = self.shortest_path(o, d)

    def get_route(self, origin: str, dest: str):
        return self._routes.get((origin, dest))

    def free_flow_time(self, route_seg_ids: list, vclass: str) -> float:
        return sum(self.segments[s].free_flow_time(vclass) for s in route_seg_ids)

    def reset_segments(self):
        """Clear all vehicles from all segments (used between runs)."""
        for seg in self.segments.values():
            seg.vehicles.clear()
