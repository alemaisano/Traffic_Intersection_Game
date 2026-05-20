"""
ui.py  –  Pygame front-end for the Traffic Signal Network Simulation.

Three screens
─────────────
  PRERUN   : scenario picker + per-intersection signal timing editor
  RUNNING  : live network map + HUD
  RESULTS  : post-run metrics dashboard
"""

import sys
import pygame
from config import (
    SCREEN_W, SCREEN_H, FPS, STEPS_PER_FRAME,
    NODE_PIXELS, INTERSECTION_NODES, BOUNDARY_ZONES, ROAD_PAIRS,
    INTERSECTION_HALF_PX, LANE_OFFSET_PX,
    DEFAULT_NS_GREEN, DEFAULT_EW_GREEN, DEFAULT_YELLOW,
    MIN_GREEN, MAX_GREEN, HORIZON,
    BLACK, WHITE, GRAY, DARK_GRAY, ROAD_C, INT_C,
    SIG_RED, SIG_YEL, SIG_GRN,
    UI_BG, UI_PANEL, HIGHLIGHT, TEXT_C, TEXT_DIM, ACCENT,
    VEHICLE_PARAMS, PIXELS_PER_METER,
)
from simulation import SimulationEngine

# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────

def _text(surf, font, msg, x, y, color=TEXT_C, anchor='topleft'):
    img = font.render(str(msg), True, color)
    r   = img.get_rect()
    setattr(r, anchor, (x, y))
    surf.blit(img, r)
    return r


def _bar(surf, x, y, w, h, value, max_val, fg, bg=DARK_GRAY):
    pygame.draw.rect(surf, bg, (x, y, w, h))
    fill = int(w * min(1.0, value / max(1, max_val)))
    if fill > 0:
        pygame.draw.rect(surf, fg, (x, y, fill, h))
    pygame.draw.rect(surf, GRAY, (x, y, w, h), 1)


def _lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ──────────────────────────────────────────────────────────────────────
# network map drawing (used on RUNNING screen)
# ──────────────────────────────────────────────────────────────────────

ROAD_WIDTH = LANE_OFFSET_PX * 2 + 6    # both lanes + kerb


def _draw_network(surf, signals_obj):
    """Draw roads, intersections, and signal indicators."""

    # --- roads ---
    drawn_pairs = set()
    for (a, b) in ROAD_PAIRS:
        key = tuple(sorted([a, b]))
        if key in drawn_pairs:
            continue
        drawn_pairs.add(key)
        ax, ay = NODE_PIXELS[a]
        bx, by = NODE_PIXELS[b]
        if ax == bx:                            # vertical road
            x1 = ax - ROAD_WIDTH // 2
            y1, y2 = min(ay, by), max(ay, by)
            pygame.draw.rect(surf, ROAD_C, (x1, y1, ROAD_WIDTH, y2 - y1))
        else:                                   # horizontal road
            y1 = ay - ROAD_WIDTH // 2
            x1, x2 = min(ax, bx), max(ax, bx)
            pygame.draw.rect(surf, ROAD_C, (x1, y1, x2 - x1, ROAD_WIDTH))

    # --- intersection boxes ---
    for iid in INTERSECTION_NODES:
        cx, cy = NODE_PIXELS[iid]
        h = INTERSECTION_HALF_PX
        pygame.draw.rect(surf, INT_C, (cx - h, cy - h, h * 2, h * 2))
        pygame.draw.rect(surf, GRAY, (cx - h, cy - h, h * 2, h * 2), 1)

    # --- signal indicators (small coloured circles at intersection approaches) ---
    if signals_obj is not None:
        R = 6
        for iid, sig in signals_obj.signals.items():
            cx, cy = NODE_PIXELS[iid]
            h = INTERSECTION_HALF_PX
            ns_col = sig.signal_color('NS')
            ew_col = sig.signal_color('EW')
            # N approach (vehicle travelling S enters from top)
            pygame.draw.circle(surf, ns_col, (cx,     cy - h - R - 2), R)
            # S approach
            pygame.draw.circle(surf, ns_col, (cx,     cy + h + R + 2), R)
            # W approach
            pygame.draw.circle(surf, ew_col, (cx - h - R - 2, cy),     R)
            # E approach
            pygame.draw.circle(surf, ew_col, (cx + h + R + 2, cy),     R)

    # --- boundary zone labels ---
    return   # labels drawn separately by caller


def _draw_zone_labels(surf, font_sm):
    label_offsets = {
        'TL': ( 0, -18), 'TR': ( 0, -18),
        'LT': (-30,  0), 'LB': (-30,  0),
        'RT': (  5,  0), 'RB': (  5,  0),
        'BL': ( 0,  10), 'BR': ( 0,  10),
    }
    for zone in BOUNDARY_ZONES:
        cx, cy = NODE_PIXELS[zone]
        ox, oy = label_offsets[zone]
        _text(surf, font_sm, zone, cx + ox, cy + oy, ACCENT, anchor='center')


def _draw_vehicles(surf, active_vehicles):
    for v in active_vehicles:
        r = v.pixel_rect()
        if r is None:
            continue
        pygame.draw.rect(surf, v.color, r)
        # thin dark outline
        pygame.draw.rect(surf, (0, 0, 0), r, 1)


# ──────────────────────────────────────────────────────────────────────
# PRE-RUN screen
# ──────────────────────────────────────────────────────────────────────

SCENARIOS_LIST = ['light', 'balanced', 'peak']
INTERSECTIONS  = ['I1', 'I2', 'I3', 'I4']

# Editable fields per intersection: index → (label, key, min, max, step)
FIELDS = [
    ('NS Green', 'ns_green', MIN_GREEN, MAX_GREEN, 1),
    ('EW Green', 'ew_green', MIN_GREEN, MAX_GREEN, 1),
    ('Yellow',   'yellow',   2,         4,         1),
]


class PreRunScreen:
    def __init__(self, font, font_sm, font_lg):
        self.font    = font
        self.font_sm = font_sm
        self.font_lg = font_lg

        self.scenario_idx = 1           # default: balanced
        self.timing = {
            iid: {
                'ns_green': DEFAULT_NS_GREEN,
                'ew_green': DEFAULT_EW_GREEN,
                'yellow':   DEFAULT_YELLOW,
            }
            for iid in INTERSECTIONS
        }

        # cursor: (intersection_idx, field_idx)
        self.cur_int   = 0
        self.cur_field = 0
        self.done      = False   # True when user presses Enter/Space to start
        self.preview_net = None  # optional: a quick demand preview

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key

        if key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()

        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self.done = True
            return

        # Scenario cycling
        if key == pygame.K_s:
            self.scenario_idx = (self.scenario_idx + 1) % len(SCENARIOS_LIST)
            return

        # Navigate intersections
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            delta = -1 if key == pygame.K_LEFT else 1
            self.cur_int = (self.cur_int + delta) % len(INTERSECTIONS)
            return

        # Navigate fields
        if key in (pygame.K_UP, pygame.K_DOWN):
            delta = -1 if key == pygame.K_UP else 1
            self.cur_field = (self.cur_field + delta) % len(FIELDS)
            return

        # Change value
        iid   = INTERSECTIONS[self.cur_int]
        label, fkey, fmin, fmax, fstep = FIELDS[self.cur_field]
        if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.timing[iid][fkey] = max(fmin, self.timing[iid][fkey] - fstep)
        if key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.timing[iid][fkey] = min(fmax, self.timing[iid][fkey] + fstep)

    # ------------------------------------------------------------------
    def draw(self, surf):
        surf.fill(UI_BG)

        # Title
        _text(surf, self.font_lg, 'TRAFFIC SIGNAL NETWORK',
              SCREEN_W // 2, 28, ACCENT, anchor='midtop')
        _text(surf, self.font_sm, 'Configure signal timing, then press ENTER to run.',
              SCREEN_W // 2, 72, TEXT_DIM, anchor='midtop')

        # Scenario row
        scen = SCENARIOS_LIST[self.scenario_idx]
        _text(surf, self.font, f'Scenario:  [ S to cycle ]    ►  {scen.upper()}',
              60, 110, WHITE)

        # Signal timing panel  (4 intersection columns)
        col_w  = 280
        col_xs = [60 + i * col_w for i in range(4)]
        row_y0 = 170

        for ci, iid in enumerate(INTERSECTIONS):
            cx = col_xs[ci]
            is_sel = (ci == self.cur_int)
            panel_color = HIGHLIGHT if is_sel else UI_PANEL
            pygame.draw.rect(surf, panel_color, (cx - 8, row_y0 - 8,
                                                  col_w - 16, 200), border_radius=6)
            pygame.draw.rect(surf, ACCENT if is_sel else GRAY,
                             (cx - 8, row_y0 - 8, col_w - 16, 200), 1, border_radius=6)

            _text(surf, self.font, iid, cx + 10, row_y0 + 4,
                  ACCENT if is_sel else TEXT_C)

            for fi, (label, fkey, fmin, fmax, fstep) in enumerate(FIELDS):
                fy = row_y0 + 44 + fi * 48
                is_field_sel = is_sel and (fi == self.cur_field)
                fc = WHITE if is_field_sel else TEXT_DIM
                val = self.timing[iid][fkey]

                _text(surf, self.font_sm, label, cx + 10, fy, fc)
                # value box
                vbox_x = cx + 148
                pygame.draw.rect(surf, DARK_GRAY, (vbox_x, fy - 2, 56, 24),
                                 border_radius=3)
                if is_field_sel:
                    pygame.draw.rect(surf, ACCENT, (vbox_x, fy - 2, 56, 24), 1,
                                     border_radius=3)
                _text(surf, self.font, str(val), vbox_x + 28, fy + 10,
                      ACCENT if is_field_sel else WHITE, anchor='center')
                # bar
                _bar(surf, cx + 10, fy + 28, col_w - 40, 6,
                     val - fmin, fmax - fmin, ACCENT)

        # Controls hint
        hints = [
            '← / →   select intersection',
            '↑ / ↓   select field',
            '+  /  −   change value',
            'S         cycle scenario',
            'ENTER   start simulation',
        ]
        for i, h in enumerate(hints):
            _text(surf, self.font_sm, h, 60, 400 + i * 26, TEXT_DIM)

        # Mini network preview (static)
        self._draw_mini_network(surf, 820, 380)

    def _draw_mini_network(self, surf, ox, oy):
        """Tiny static preview of the 4-intersection grid."""
        scale  = 0.28
        radius = 10

        def sp(name):
            px, py = NODE_PIXELS[name]
            return (int(ox + px * scale), int(oy + py * scale - 200 * scale))

        for (a, b) in ROAD_PAIRS:
            ax, ay = sp(a)
            bx, by = sp(b)
            pygame.draw.line(surf, ROAD_C, (ax, ay), (bx, by), 4)

        for iid in INTERSECTION_NODES:
            cx, cy = sp(iid)
            pygame.draw.rect(surf, INT_C,
                             (cx - radius, cy - radius, radius * 2, radius * 2))
            _text(surf, self.font_sm, iid, cx, cy, ACCENT, anchor='center')

        for zone in BOUNDARY_ZONES:
            cx, cy = sp(zone)
            pygame.draw.circle(surf, GRAY, (cx, cy), 5)
            _text(surf, self.font_sm, zone, cx, cy - 10, TEXT_DIM, anchor='center')

    @property
    def scenario(self):
        return SCENARIOS_LIST[self.scenario_idx]


# ──────────────────────────────────────────────────────────────────────
# RUNNING screen
# ──────────────────────────────────────────────────────────────────────

class RunningScreen:
    def __init__(self, engine: SimulationEngine, font, font_sm, font_lg):
        self.engine   = engine
        self.font     = font
        self.font_sm  = font_sm
        self.font_lg  = font_lg
        self.paused   = False
        self.speed    = STEPS_PER_FRAME   # steps per rendered frame

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if event.key == pygame.K_p:
            self.paused = not self.paused
        if event.key == pygame.K_EQUALS or event.key == pygame.K_KP_PLUS:
            self.speed = min(self.speed + 1, 10)
        if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
            self.speed = max(self.speed - 1, 1)

    def update(self):
        if self.paused or self.engine.done:
            return
        for _ in range(self.speed):
            self.engine.step()
            if self.engine.done:
                break

    def draw(self, surf):
        surf.fill(UI_BG)

        # Network
        _draw_network(surf, self.engine.signals)
        _draw_zone_labels(surf, self.font_sm)
        _draw_vehicles(surf, self.engine.active_vehicles())

        # HUD panel (right side)
        self._draw_hud(surf)

    def _draw_hud(self, surf):
        hx, hy = SCREEN_W - 240, 10
        hw, hh = 228, SCREEN_H - 20
        pygame.draw.rect(surf, UI_PANEL, (hx, hy, hw, hh), border_radius=6)
        pygame.draw.rect(surf, GRAY, (hx, hy, hw, hh), 1, border_radius=6)

        y = hy + 14
        _text(surf, self.font_lg, 'HUD', hx + hw // 2, y, ACCENT, anchor='midtop')
        y += 36

        # Time
        elapsed = self.engine.sim_time
        pct     = elapsed / HORIZON
        _text(surf, self.font_sm, f'Time  {elapsed:5.1f} / {HORIZON:.0f} s',
              hx + 10, y, TEXT_C)
        y += 20
        _bar(surf, hx + 10, y, hw - 20, 8, elapsed, HORIZON, ACCENT)
        y += 18

        if self.paused:
            _text(surf, self.font, '[ PAUSED ]', hx + hw // 2, y, SIG_YEL,
                  anchor='midtop')
        else:
            spd_col = SIG_GRN if self.speed > 1 else TEXT_DIM
            _text(surf, self.font_sm, f'Speed ×{self.speed}', hx + 10, y, spd_col)
        y += 28

        # Vehicle counts
        cts = self.engine.counts()
        pygame.draw.line(surf, DARK_GRAY, (hx + 8, y), (hx + hw - 8, y))
        y += 8
        rows = [
            ('Total',     cts['total'],   TEXT_C),
            ('Active',    cts['active'],  SIG_GRN),
            ('Pending',   cts['pending'], TEXT_DIM),
            ('Completed', cts['done'],    ACCENT),
        ]
        for label, val, col in rows:
            _text(surf, self.font_sm, label,       hx + 10, y, TEXT_DIM)
            _text(surf, self.font,   str(val),     hx + hw - 14, y, col, anchor='topright')
            y += 22

        # Per-intersection signal state
        pygame.draw.line(surf, DARK_GRAY, (hx + 8, y + 4), (hx + hw - 8, y + 4))
        y += 14
        _text(surf, self.font_sm, 'Signals', hx + 10, y, TEXT_DIM)
        y += 22
        for iid, sig in self.engine.signals.signals.items():
            phase_str = sig.active_phase
            col = (SIG_GRN if 'GREEN' in phase_str else
                   SIG_YEL if 'YELLOW' in phase_str else SIG_RED)
            _text(surf, self.font_sm, f'{iid}  {phase_str}  {sig.time_remaining:.1f}s',
                  hx + 10, y, col)
            y += 20

        # Per-intersection queue
        pygame.draw.line(surf, DARK_GRAY, (hx + 8, y + 4), (hx + hw - 8, y + 4))
        y += 14
        _text(surf, self.font_sm, 'Queues', hx + 10, y, TEXT_DIM)
        y += 22
        for seg in self.engine.network.segments.values():
            if seg.enters_intersection and seg.vehicles:
                iid = seg.enters_intersection
                _text(surf, self.font_sm,
                      f'{seg.from_node}→{iid}: {len(seg.vehicles)}',
                      hx + 10, y, TEXT_C)
                y += 18
                if y > hy + hh - 40:
                    break

        # Controls
        pygame.draw.line(surf, DARK_GRAY, (hx + 8, y + 4), (hx + hw - 8, y + 4))
        y += 14
        for hint in ['P  pause', '+ / −  speed']:
            _text(surf, self.font_sm, hint, hx + 10, y, TEXT_DIM)
            y += 18


# ──────────────────────────────────────────────────────────────────────
# RESULTS screen
# ──────────────────────────────────────────────────────────────────────

class ResultsScreen:
    def __init__(self, metrics: dict, font, font_sm, font_lg):
        self.m       = metrics
        self.font    = font
        self.font_sm = font_sm
        self.font_lg = font_lg
        self.restart = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
            self.restart = True

    def draw(self, surf):
        surf.fill(UI_BG)
        m = self.m

        _text(surf, self.font_lg, 'RESULTS', SCREEN_W // 2, 24, ACCENT, anchor='midtop')

        # ── main KPIs ──
        kpi_y = 90
        kpi_w = 320

        def kpi(label, value_str, col, x, y):
            pygame.draw.rect(surf, UI_PANEL, (x, y, kpi_w, 90), border_radius=8)
            pygame.draw.rect(surf, col, (x, y, kpi_w, 90), 1, border_radius=8)
            _text(surf, self.font_sm, label, x + kpi_w // 2, y + 10, TEXT_DIM, anchor='midtop')
            _text(surf, self.font_lg, value_str, x + kpi_w // 2, y + 35, col, anchor='midtop')

        throughput_pct = int(m['throughput'] * 100)
        equity_pct     = int(m['equity'] * 100)
        t_col = SIG_GRN if throughput_pct >= 70 else (SIG_YEL if throughput_pct >= 40 else SIG_RED)
        e_col = SIG_GRN if equity_pct     >= 70 else (SIG_YEL if equity_pct     >= 40 else SIG_RED)

        kpi('Throughput',     f"{throughput_pct}%",         t_col, 50,  kpi_y)
        kpi('Equity',         f"{equity_pct}%",             e_col, 390, kpi_y)
        kpi('Avg Delay',      f"{m['avg_delay']:.1f} s",    ACCENT, 730, kpi_y)
        kpi('Trips Completed', f"{m['completed']} / {m['total']}", TEXT_C, 1070, kpi_y)

        # ── queue stats ──
        y = kpi_y + 120
        _text(surf, self.font, 'Residual queues at end of run:', 50, y, TEXT_C)
        y += 30
        for iid, q in sorted(m['queue_stats'].items()):
            bot = '  ← bottleneck' if iid == m['bottleneck'] else ''
            col = SIG_RED if iid == m['bottleneck'] else TEXT_C
            _text(surf, self.font_sm, f'  {iid}: {q} vehicles{bot}', 50, y, col)
            y += 24

        # ── per-OD delay summary ──
        y += 16
        _text(surf, self.font, 'Per-OD delay sample (worst 8 pairs):', 50, y, TEXT_C)
        y += 30
        od_sorted = sorted(
            [(k, sum(v)/len(v)) for k, v in m['od_delays'].items() if v],
            key=lambda x: -x[1]
        )[:8]
        for (o, d), avg in od_sorted:
            bar_val = min(avg, 60.0)
            col = _lerp_color(SIG_GRN, SIG_RED, bar_val / 60.0)
            _text(surf, self.font_sm, f'{o}→{d}', 50, y, TEXT_DIM)
            _bar(surf, 160, y + 2, 300, 16, bar_val, 60.0, col)
            _text(surf, self.font_sm, f'{avg:.1f}s', 470, y, TEXT_C)
            y += 26
            if y > SCREEN_H - 80:
                break

        # ── restart hint ──
        _text(surf, self.font, 'Press R or ENTER to play again  |  ESC to quit',
              SCREEN_W // 2, SCREEN_H - 40, TEXT_DIM, anchor='midtop')


# ──────────────────────────────────────────────────────────────────────
# Application loop
# ──────────────────────────────────────────────────────────────────────

def run():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption('Traffic Signal Network Simulation')
    clock = pygame.time.Clock()

    font_lg = pygame.font.Font(None, 48)
    font    = pygame.font.Font(None, 30)
    font_sm = pygame.font.Font(None, 22)

    while True:
        # ── PRERUN ──
        pre = PreRunScreen(font, font_sm, font_lg)
        while not pre.done:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                pre.handle_event(ev)
            pre.draw(screen)
            pygame.display.flip()

        # ── BUILD ENGINE ──
        engine  = SimulationEngine(timing=pre.timing, scenario=pre.scenario)
        running = RunningScreen(engine, font, font_sm, font_lg)

        # ── RUNNING ──
        while not engine.done:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                running.handle_event(ev)
            running.update()
            running.draw(screen)
            pygame.display.flip()

        # Draw one last frame with final state
        running.draw(screen)
        pygame.display.flip()
        pygame.time.wait(600)

        # ── RESULTS ──
        results = ResultsScreen(engine.metrics, font, font_sm, font_lg)
        while not results.restart:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                results.handle_event(ev)
            results.draw(screen)
            pygame.display.flip()
