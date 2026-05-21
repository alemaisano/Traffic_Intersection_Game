from config import STANDARD_NS_GREEN, STANDARD_EW_GREEN, STANDARD_YELLOW, SIG_GRN, SIG_YEL, SIG_RED

NS_DIRS = {'N', 'S'}
EW_DIRS = {'E', 'W'}

GREEN  = 'GREEN'
YELLOW = 'YELLOW'


class IntersectionSignal:
    """2-phase (NS / EW) fixed-timing signal controller for one intersection."""

    def __init__(self, intersection_id, start_phase='NS', start_offset=0.0):
        self.iid      = intersection_id
        self.ns_green = STANDARD_NS_GREEN
        self.ew_green = STANDARD_EW_GREEN
        self.yellow   = STANDARD_YELLOW

        self._phase = f'{start_phase}_{GREEN}'
        duration    = self.ns_green if start_phase == 'NS' else self.ew_green
        self._timer = max(0.1, duration - start_offset)

    def step(self, dt):
        self._timer -= dt
        if self._timer > 0:
            return
        transitions = {
            'NS_GREEN':  ('NS_YELLOW', self.yellow),
            'NS_YELLOW': ('EW_GREEN',  self.ew_green),
            'EW_GREEN':  ('EW_YELLOW', self.yellow),
            'EW_YELLOW': ('NS_GREEN',  self.ns_green),
        }
        self._phase, self._timer = transitions[self._phase]

    def force_green(self, group):
        """Immediately switch to NS or EW green (player override)."""
        self._phase = f'{group}_GREEN'
        self._timer = float(self.ns_green if group == 'NS' else self.ew_green)

    def is_green_for(self, direction):
        if self._phase == 'NS_GREEN':
            return direction in NS_DIRS
        if self._phase == 'EW_GREEN':
            return direction in EW_DIRS
        return False

    @property
    def active_phase(self):
        return self._phase

    @property
    def time_remaining(self):
        return max(0.0, self._timer)

    def signal_color(self, group):
        """'NS' or 'EW' → RGB colour for map rendering."""
        if group == 'NS':
            if self._phase == 'NS_GREEN':  return SIG_GRN
            if self._phase == 'NS_YELLOW': return SIG_YEL
            return SIG_RED
        else:
            if self._phase == 'EW_GREEN':  return SIG_GRN
            if self._phase == 'EW_YELLOW': return SIG_YEL
            return SIG_RED


class NetworkSignals:
    """One IntersectionSignal per intersection, initialised from map signal_config."""

    def __init__(self, intersection_ids, signal_config=None):
        signal_config = signal_config or {}
        self.signals = {}
        for iid in intersection_ids:
            cfg = signal_config.get(iid, {})
            self.signals[iid] = IntersectionSignal(
                iid,
                start_phase=cfg.get('start_phase', 'NS'),
                start_offset=cfg.get('start_offset', 0.0),
            )

    def step(self, dt):
        for sig in self.signals.values():
            sig.step(dt)

    def is_green_for_segment(self, segment):
        if segment.enters_intersection is None:
            return True
        return self.signals[segment.enters_intersection].is_green_for(segment.direction)
