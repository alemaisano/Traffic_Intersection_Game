from config import (DEFAULT_NS_GREEN, DEFAULT_EW_GREEN, DEFAULT_YELLOW,
                    MIN_GREEN, MAX_GREEN, SIG_GRN, SIG_YEL, SIG_RED)

NS_DIRS = {'N', 'S'}
EW_DIRS = {'E', 'W'}

GREEN  = 'GREEN'
YELLOW = 'YELLOW'


class IntersectionSignal:
    """2-phase (NS / EW) signal controller for one intersection."""

    def __init__(self, intersection_id,
                 ns_green=DEFAULT_NS_GREEN,
                 ew_green=DEFAULT_EW_GREEN,
                 yellow=DEFAULT_YELLOW,
                 start_phase='NS',
                 start_offset=0.0):
        self.iid = intersection_id
        self.ns_green = ns_green
        self.ew_green = ew_green
        self.yellow   = yellow

        # phase: 'NS_GREEN', 'NS_YELLOW', 'EW_GREEN', 'EW_YELLOW'
        self._phase = f'{start_phase}_{GREEN}'
        self._timer = (ns_green if start_phase == 'NS' else ew_green) - start_offset
        if self._timer <= 0:
            self._timer = 0.1

    # ------------------------------------------------------------------
    def configure(self, ns_green, ew_green, yellow):
        self.ns_green = max(MIN_GREEN, min(MAX_GREEN, int(ns_green)))
        self.ew_green = max(MIN_GREEN, min(MAX_GREEN, int(ew_green)))
        self.yellow   = max(2, min(4, int(yellow)))
        self._phase   = 'NS_GREEN'
        self._timer   = float(self.ns_green)

    # ------------------------------------------------------------------
    def step(self, dt: float):
        self._timer -= dt
        if self._timer > 0:
            return
        # Advance to next phase
        transitions = {
            'NS_GREEN':  ('NS_YELLOW', self.yellow),
            'NS_YELLOW': ('EW_GREEN',  self.ew_green),
            'EW_GREEN':  ('EW_YELLOW', self.yellow),
            'EW_YELLOW': ('NS_GREEN',  self.ns_green),
        }
        self._phase, self._timer = transitions[self._phase]

    # ------------------------------------------------------------------
    def is_green_for(self, direction: str) -> bool:
        if self._phase == 'NS_GREEN':
            return direction in NS_DIRS
        if self._phase == 'EW_GREEN':
            return direction in EW_DIRS
        return False   # yellow phases: no one goes

    @property
    def active_phase(self) -> str:
        return self._phase

    @property
    def time_remaining(self) -> float:
        return max(0.0, self._timer)

    def signal_color(self, group: str) -> tuple:
        """'NS' or 'EW' → RGB colour to display on the map."""
        if group == 'NS':
            if self._phase == 'NS_GREEN':  return SIG_GRN
            if self._phase == 'NS_YELLOW': return SIG_YEL
            return SIG_RED
        else:
            if self._phase == 'EW_GREEN':  return SIG_GRN
            if self._phase == 'EW_YELLOW': return SIG_YEL
            return SIG_RED


class NetworkSignals:
    """Manages one IntersectionSignal per intersection, with staggered starts."""

    def __init__(self):
        self.signals: dict[str, IntersectionSignal] = {
            'I1': IntersectionSignal('I1', start_phase='NS', start_offset=0.0),
            'I2': IntersectionSignal('I2', start_phase='EW', start_offset=0.0),
            'I3': IntersectionSignal('I3', start_phase='EW', start_offset=0.0),
            'I4': IntersectionSignal('I4', start_phase='NS', start_offset=0.0),
        }

    def apply_timing(self, timing: dict):
        """timing = {'I1': {'ns_green':15,'ew_green':15,'yellow':3}, ...}"""
        for iid, cfg in timing.items():
            if iid in self.signals:
                self.signals[iid].configure(
                    cfg.get('ns_green', DEFAULT_NS_GREEN),
                    cfg.get('ew_green', DEFAULT_EW_GREEN),
                    cfg.get('yellow',   DEFAULT_YELLOW),
                )

    def step(self, dt: float):
        for sig in self.signals.values():
            sig.step(dt)

    def is_green_for_segment(self, segment) -> bool:
        if segment.enters_intersection is None:
            return True
        return self.signals[segment.enters_intersection].is_green_for(segment.direction)
