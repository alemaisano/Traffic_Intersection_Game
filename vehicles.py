from config import (VEHICLE_PARAMS, STOPPING_GAP, MOVING_GAP, DT,
                    PIXELS_PER_METER)

PENDING = 'PENDING'
ACTIVE  = 'ACTIVE'
DONE    = 'DONE'

_id_counter = 0


def _next_id():
    global _id_counter
    _id_counter += 1
    return _id_counter


def reset_id_counter():
    global _id_counter
    _id_counter = 0


class Vehicle:
    """A single vehicle travelling a pre-computed route through the network."""

    __slots__ = ('vid', 'vclass', 'max_speed', 'accel', 'decel', 'length',
                 'color', 'weight', 'route', 'route_idx', 'network',
                 'depart_time', 'state', 'velocity', 'dist_on_seg',
                 'actual_depart', 'actual_arrive', 'delay',
                 'origin_zone', 'dest_zone')

    def __init__(self, vclass: str, route_seg_ids: list, network, depart_time: float):
        self.vid        = _next_id()
        self.vclass     = vclass
        p               = VEHICLE_PARAMS[vclass]
        self.max_speed  = p['max_speed']
        self.accel      = p['accel']
        self.decel      = p['decel']
        self.length     = p['length']
        self.color      = p['color']
        self.weight     = p['weight']

        self.route      = route_seg_ids[:]
        self.route_idx  = 0
        self.network    = network

        self.depart_time   = depart_time
        self.state         = PENDING
        self.velocity      = 0.0
        self.dist_on_seg   = 0.0

        self.actual_depart = None
        self.actual_arrive = None
        self.delay         = 0.0
        self.origin_zone   = None
        self.dest_zone     = None

    # ------------------------------------------------------------------
    @property
    def current_segment(self):
        if self.route_idx < len(self.route):
            return self.network.segments[self.route[self.route_idx]]
        return None

    @property
    def front_dist(self) -> float:
        """Distance of vehicle FRONT from segment start (= dist_on_seg)."""
        return self.dist_on_seg

    @property
    def rear_dist(self) -> float:
        return self.dist_on_seg - self.length

    # ------------------------------------------------------------------
    def activate(self, sim_time: float):
        self.state         = ACTIVE
        self.actual_depart = sim_time
        seg = self.current_segment
        # Place vehicle rear at segment start; front at length
        self.dist_on_seg = self.length
        self.velocity    = 0.0
        seg.vehicles.append(self)           # appended = back of queue

    # ------------------------------------------------------------------
    def pixel_pos(self):
        """Centre-of-vehicle screen position, or None if not active."""
        seg = self.current_segment
        if seg is None:
            return None
        mid = self.dist_on_seg - self.length / 2.0
        return seg.pixel_at(max(0.0, mid))

    def pixel_rect(self):
        """(x, y, w, h) rectangle for rendering; oriented along segment direction."""
        seg = self.current_segment
        if seg is None:
            return None
        px, py = self.pixel_pos()
        len_px = self.length * PIXELS_PER_METER
        w_px   = 7   # lane width in pixels
        d = seg.direction
        if d in ('E', 'W'):
            return (int(px - len_px / 2), int(py - w_px / 2),
                    int(len_px), w_px)
        else:
            return (int(px - w_px / 2), int(py - len_px / 2),
                    w_px, int(len_px))

    # ------------------------------------------------------------------
    def _gap_to_ahead(self) -> float:
        """Gap (metres) between self's front and the rear of the vehicle ahead."""
        seg = self.current_segment
        idx = seg.vehicles.index(self)
        if idx == 0:
            return float('inf')
        ahead = seg.vehicles[idx - 1]   # lower index = closer to segment end
        gap = ahead.rear_dist - self.front_dist
        return max(0.0, gap)

    # ------------------------------------------------------------------
    def step(self, dt: float, signals, sim_time: float):
        if self.state != ACTIVE:
            return
        seg = self.current_segment
        if seg is None:
            return

        signal_green  = signals.is_green_for_segment(seg)
        stop_line     = seg.stop_line_m
        dist_to_stop  = stop_line - self.dist_on_seg
        gap_ahead     = self._gap_to_ahead()

        # --- desired speed ---
        must_yield_signal = (not signal_green) and (dist_to_stop > 0)

        if must_yield_signal:
            # Decelerate to stop at stop line
            braking_needed = (self.velocity ** 2) / (2.0 * self.decel + 1e-6)
            if dist_to_stop <= braking_needed + 1.0:
                target_v = 0.0
            else:
                target_v = self.max_speed
        else:
            target_v = self.max_speed

        # Slow for vehicle ahead
        if gap_ahead < STOPPING_GAP:
            target_v = 0.0
        elif gap_ahead < MOVING_GAP + 4.0:
            target_v = min(target_v, self.max_speed * 0.35)

        # Accelerate / decelerate
        if self.velocity < target_v:
            self.velocity = min(target_v, self.velocity + self.accel * dt)
        else:
            self.velocity = max(target_v, self.velocity - self.decel * dt)
        self.velocity = max(0.0, self.velocity)

        # Hard clamp at stop line when red
        proposed = self.dist_on_seg + self.velocity * dt
        if must_yield_signal and proposed >= stop_line - 0.05:
            self.dist_on_seg = stop_line - 0.05
            self.velocity    = 0.0
        else:
            self.dist_on_seg = proposed

        # Advance to next segment if we've crossed the end
        if self.dist_on_seg >= seg.length_m:
            self._advance_segment(seg, sim_time)

    # ------------------------------------------------------------------
    def _advance_segment(self, old_seg, sim_time: float):
        overflow = self.dist_on_seg - old_seg.length_m
        old_seg.vehicles.remove(self)
        self.route_idx += 1
        if self.route_idx >= len(self.route):
            self.state         = DONE
            self.actual_arrive = sim_time
            return
        new_seg = self.current_segment
        self.dist_on_seg = self.length + max(0.0, overflow)
        new_seg.vehicles.append(self)
