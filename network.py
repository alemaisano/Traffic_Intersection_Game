import math
import heapq
from config import PIXELS_PER_METER, LANE_OFFSET_PX, INTERSECTION_HALF_M, VEHICLE_PARAMS


def _direction(from_px, to_px):
    dx, dy = to_px[0] - from_px[0], to_px[1] - from_px[1]
    if abs(dx) >= abs(dy):
        return 'E' if dx > 0 else 'W'
    return 'S' if dy > 0 else 'N'


def _pixel_dist(from_px, to_px):
    dx, dy = to_px[0] - from_px[0], to_px[1] - from_px[1]
    return math.sqrt(dx * dx + dy * dy)


def _lane_endpoints(from_px, to_px):
    """
    Lane centre pixels for right-hand traffic.

    Given travel direction unit vector (ux, uy), the right-side lane offset
    (in screen coords where y increases downward) is (-uy, ux):
      East  (1, 0)  → offset (0, +1)  = south lane  ✓
      West  (-1, 0) → offset (0, -1)  = north lane  ✓
      South (0, +1) → offset (-1, 0)  = west lane   ✓
      North (0, -1) → offset (+1, 0)  = east lane   ✓
    """
    dx, dy = to_px[0] - from_px[0], to_px[1] - from_px[1]
    dist   = math.sqrt(dx * dx + dy * dy)
    ux, uy = dx / dist, dy / dist
    ox, oy = -uy * LANE_OFFSET_PX, ux * LANE_OFFSET_PX   # right-hand offset
    return (from_px[0] + ox, from_px[1] + oy), (to_px[0] + ox, to_px[1] + oy)


class Segment:
    """One directed road segment between two network nodes."""

    __slots__ = ('id', 'from_node', 'to_node', 'direction', 'length_m',
                 'px_start', 'px_end', 'enters_intersection', 'stop_line_m',
                 'vehicles')

    def __init__(self, seg_id, from_node, to_node, node_pixels, intersection_nodes):
        self.id        = seg_id
        self.from_node = from_node
        self.to_node   = to_node
        from_px = node_pixels[from_node]
        to_px   = node_pixels[to_node]
        self.direction = _direction(from_px, to_px)
        px_len         = _pixel_dist(from_px, to_px)
        self.length_m  = px_len / PIXELS_PER_METER
        self.px_start, self.px_end = _lane_endpoints(from_px, to_px)
        self.enters_intersection   = to_node if to_node in intersection_nodes else None
        self.stop_line_m = (self.length_m - INTERSECTION_HALF_M
                            if self.enters_intersection else self.length_m)
        self.vehicles = []   # ordered: index 0 = closest to segment end (front)

    def pixel_at(self, dist_m):
        """Screen pixel at dist_m along this segment's lane."""
        t = max(0.0, min(1.0, dist_m / self.length_m))
        sx, sy = self.px_start
        ex, ey = self.px_end
        return (sx + (ex - sx) * t, sy + (ey - sy) * t)

    def free_flow_time(self, vclass):
        return self.length_m / VEHICLE_PARAMS[vclass]['max_speed']


class Network:
    def __init__(self, map_def):
        self.node_pixels       = map_def['node_pixels']
        self.intersection_nodes = map_def['intersection_nodes']
        self.boundary_zones    = map_def['boundary_zones']
        self.road_pairs        = map_def['road_pairs']

        self.segments = {}
        self.adj      = {}    # from_node -> [(to_node, seg_id, length_m)]
        self._routes  = {}
        self._build()

    def _build(self):
        for (a, b) in self.road_pairs:
            for frm, to in ((a, b), (b, a)):
                sid = f"{frm}->{to}"
                seg = Segment(sid, frm, to, self.node_pixels, self.intersection_nodes)
                self.segments[sid] = seg
                self.adj.setdefault(frm, []).append((to, sid, seg.length_m))

    # ------------------------------------------------------------------
    def shortest_path(self, origin, dest):
        """Dijkstra. Returns list of seg_ids or None."""
        dist = {n: float('inf') for n in self.node_pixels}
        prev = {n: None for n in self.node_pixels}
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
        for o in self.boundary_zones:
            for d in self.boundary_zones:
                if o != d:
                    self._routes[(o, d)] = self.shortest_path(o, d)

    def get_route(self, origin, dest):
        return self._routes.get((origin, dest))

    def free_flow_time(self, route_seg_ids, vclass):
        return sum(self.segments[s].free_flow_time(vclass) for s in route_seg_ids)

    def reset_segments(self):
        for seg in self.segments.values():
            seg.vehicles.clear()
