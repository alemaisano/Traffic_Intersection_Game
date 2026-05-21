"""
ui.py  –  Pygame front-end for the Traffic Signal Network Simulation.

Three screens
─────────────
  PRERUN   : map selector + scenario picker
  RUNNING  : live network map + HUD
  RESULTS  : post-run metrics dashboard
"""

import sys
import os
import pygame
from config import (
    SCREEN_W, SCREEN_H, FPS, HORIZON,
    PIXELS_PER_METER, LANE_OFFSET_PX, INTERSECTION_HALF_PX,
    BLACK, WHITE, GRAY, DARK_GRAY, ROAD_C, CENTRE_C, INT_C,
    SIG_RED, SIG_YEL, SIG_GRN,
    UI_BG, UI_PANEL, HIGHLIGHT, TEXT_C, TEXT_DIM, ACCENT,
)
from maps import MAPS, MAP_ORDER
from simulation import SimulationEngine
from scores import save_run

# ──────────────────────────────────────────────────────────────────────
# Direction → image subdirectory mapping
# ──────────────────────────────────────────────────────────────────────
_DIR_IMG = {'E': 'right', 'W': 'left', 'S': 'down', 'N': 'up'}

ROAD_WIDTH = LANE_OFFSET_PX * 2 + 4   # total road width in pixels

# Car image pixel dimensions (scaled to fit the lane)
CAR_LONG = max(20, int(4.5 * PIXELS_PER_METER))   # along direction of travel
CAR_WIDE = LANE_OFFSET_PX * 2 - 4                  # across direction of travel


# ──────────────────────────────────────────────────────────────────────
# Asset loading
# ──────────────────────────────────────────────────────────────────────

def _load_car_images():
    """Return {direction: scaled_Surface} for E/W/N/S."""
    images = {}
    for direction, subdir in _DIR_IMG.items():
        path = os.path.join('images', subdir, 'car.png')
        try:
            img = pygame.image.load(path).convert_alpha()
        except pygame.error:
            # Fallback: plain coloured rectangle
            if direction in ('E', 'W'):
                img = pygame.Surface((CAR_LONG, CAR_WIDE), pygame.SRCALPHA)
            else:
                img = pygame.Surface((CAR_WIDE, CAR_LONG), pygame.SRCALPHA)
            img.fill((100, 149, 237))
        # Scale to lane size
        if direction in ('E', 'W'):
            img = pygame.transform.scale(img, (CAR_LONG, CAR_WIDE))
        else:
            img = pygame.transform.scale(img, (CAR_WIDE, CAR_LONG))
        images[direction] = img
    return images


# ──────────────────────────────────────────────────────────────────────
# Common drawing helpers
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
# Network map drawing (RUNNING screen)
# ──────────────────────────────────────────────────────────────────────

def _draw_network(surf, network, signals_obj, font_sm, selected_iid=None):
    node_px  = network.node_pixels
    pairs    = network.road_pairs
    i_nodes  = network.intersection_nodes
    iid_list = sorted(i_nodes)

    # --- roads ---
    drawn = set()
    for (a, b) in pairs:
        key = tuple(sorted([a, b]))
        if key in drawn:
            continue
        drawn.add(key)
        ax, ay = node_px[a]
        bx, by = node_px[b]
        if ax == bx:    # vertical
            x1 = ax - ROAD_WIDTH // 2
            y1, y2 = min(ay, by), max(ay, by)
            pygame.draw.rect(surf, ROAD_C, (x1, y1, ROAD_WIDTH, y2 - y1))
            # centre line
            pygame.draw.line(surf, CENTRE_C, (ax, y1), (ax, y2), 1)
        else:           # horizontal
            y1 = ay - ROAD_WIDTH // 2
            x1, x2 = min(ax, bx), max(ax, bx)
            pygame.draw.rect(surf, ROAD_C, (x1, y1, x2 - x1, ROAD_WIDTH))
            pygame.draw.line(surf, CENTRE_C, (x1, ay), (x2, ay), 1)

    # --- intersection boxes ---
    for iid in i_nodes:
        cx, cy = node_px[iid]
        h = INTERSECTION_HALF_PX
        pygame.draw.rect(surf, INT_C, (cx - h, cy - h, h * 2, h * 2))
        pygame.draw.rect(surf, GRAY,  (cx - h, cy - h, h * 2, h * 2), 1)
        if iid == selected_iid:
            pygame.draw.rect(surf, ACCENT, (cx - h - 4, cy - h - 4, h*2+8, h*2+8), 2, border_radius=4)
        idx_label = str(iid_list.index(iid) + 1) if iid in iid_list else ''
        _text(surf, font_sm, idx_label, cx, cy - h - 14, ACCENT, anchor='center')

    # --- signal indicators ---
    if signals_obj is not None:
        R = 5
        for iid, sig in signals_obj.signals.items():
            cx, cy = node_px[iid]
            h = INTERSECTION_HALF_PX
            ns_col = sig.signal_color('NS')
            ew_col = sig.signal_color('EW')
            pygame.draw.circle(surf, ns_col, (cx,         cy - h - R - 2), R)
            pygame.draw.circle(surf, ns_col, (cx,         cy + h + R + 2), R)
            pygame.draw.circle(surf, ew_col, (cx - h - R - 2, cy),         R)
            pygame.draw.circle(surf, ew_col, (cx + h + R + 2, cy),         R)

    # --- zone labels ---
    label_nudge = {
        # adjusted per zone position so labels don't overlap roads
    }
    for zone in network.boundary_zones:
        cx, cy = node_px[zone]
        _text(surf, font_sm, zone, cx, cy - 12, ACCENT, anchor='center')


def _draw_vehicles(surf, active_vehicles, car_images):
    for v in active_vehicles:
        seg = v.current_segment
        if seg is None:
            continue
        cx, cy = v.pixel_pos()
        img = car_images.get(seg.direction)
        if img is None:
            continue
        rect = img.get_rect(center=(int(cx), int(cy)))
        surf.blit(img, rect)


# ──────────────────────────────────────────────────────────────────────
# PRE-RUN screen  (map + scenario selection)
# ──────────────────────────────────────────────────────────────────────

SCENARIOS_LIST = ['light', 'balanced', 'peak']


class PreRunScreen:
    def __init__(self, font, font_sm, font_lg):
        self.font    = font
        self.font_sm = font_sm
        self.font_lg = font_lg

        self.map_idx      = 0
        self.scenario_idx = 1    # default: balanced
        self.done         = False

    # --- input ---
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if k in (pygame.K_RETURN, pygame.K_SPACE):
            self.done = True
            return
        if k == pygame.K_UP:
            self.map_idx = (self.map_idx - 1) % len(MAP_ORDER)
        if k == pygame.K_DOWN:
            self.map_idx = (self.map_idx + 1) % len(MAP_ORDER)
        if k in (pygame.K_LEFT, pygame.K_RIGHT):
            d = -1 if k == pygame.K_LEFT else 1
            self.scenario_idx = (self.scenario_idx + d) % len(SCENARIOS_LIST)

    # --- draw ---
    def draw(self, surf):
        surf.fill(UI_BG)

        # ── Title ───────────────────────────────────────────────────────
        _text(surf, self.font_lg, 'ADAPTIVE TRAFFIC CONTROL',
              SCREEN_W // 2, 16, ACCENT, anchor='midtop')
        _text(surf, self.font_sm, 'A SERIOUS GAME FOR REAL-TIME SIGNAL MANAGEMENT',
              SCREEN_W // 2, 48, TEXT_DIM, anchor='midtop')

        # ── Intro block ─────────────────────────────────────────────────
        intro = [
            'Vehicles arrive randomly at the network boundary and route to their destination.',
            'Intersections run fixed 20-second NS / EW cycles — queues build when phases lag demand.',
            'Click an intersection (or press 1-6), then N or E to force a green phase.',
            'Goal: minimise delays, while maximising throughput and equity!',
        ]
        iy = 72
        for line in intro:
            _text(surf, self.font_sm, line, SCREEN_W // 2, iy, TEXT_DIM, anchor='midtop')
            iy += 17

        # ── Map list (left panel) ────────────────────────────────────────
        LIST_X, LIST_Y = 30, 148
        LIST_W, LIST_H = 370, 44

        _text(surf, self.font_sm, '↑ / ↓   select map', LIST_X, LIST_Y - 22, TEXT_DIM)

        for i, key in enumerate(MAP_ORDER):
            m   = MAPS[key]
            y   = LIST_Y + i * (LIST_H + 6)
            sel = (i == self.map_idx)
            bg  = HIGHLIGHT if sel else UI_PANEL
            pygame.draw.rect(surf, bg, (LIST_X, y, LIST_W, LIST_H), border_radius=6)
            if sel:
                pygame.draw.rect(surf, ACCENT, (LIST_X, y, LIST_W, LIST_H), 1, border_radius=6)
            col = ACCENT if sel else TEXT_C
            _text(surf, self.font,    m['name'],        LIST_X + 12, y + 6,  col)
            _text(surf, self.font_sm, m['description'], LIST_X + 12, y + 26, TEXT_DIM)

        # ── Scenario strip (below list) ──────────────────────────────────
        scen_y = LIST_Y + len(MAP_ORDER) * (LIST_H + 6) + 14
        _text(surf, self.font_sm, '← / →   scenario', LIST_X, scen_y, TEXT_DIM)
        scen_y += 20
        for i, s in enumerate(SCENARIOS_LIST):
            sel = (i == self.scenario_idx)
            col = (ACCENT if sel else GRAY)
            bw  = 110
            bx  = LIST_X + i * (bw + 8)
            pygame.draw.rect(surf, UI_PANEL if not sel else HIGHLIGHT,
                             (bx, scen_y, bw, 34), border_radius=5)
            if sel:
                pygame.draw.rect(surf, ACCENT, (bx, scen_y, bw, 34), 1, border_radius=5)
            _text(surf, self.font, s.upper(), bx + bw // 2, scen_y + 17, col, anchor='center')

        # ── Hint ─────────────────────────────────────────────────────────
        _text(surf, self.font, 'ENTER  →  start',
              LIST_X, scen_y + 48, WHITE)

        # ── Map preview (right side) ─────────────────────────────────────
        self._draw_preview(surf, MAP_ORDER[self.map_idx], 430, 148, 450, 460)

    def _draw_preview(self, surf, map_key, ox, oy, pw, ph):
        """Draw a small static map preview in a box at (ox,oy) size pw×ph."""
        m = MAPS[map_key]
        pygame.draw.rect(surf, UI_PANEL, (ox, oy, pw, ph), border_radius=8)
        pygame.draw.rect(surf, GRAY,     (ox, oy, pw, ph), 1, border_radius=8)

        node_px = m['node_pixels']
        # Compute bounding box of the map nodes
        xs = [p[0] for p in node_px.values()]
        ys = [p[1] for p in node_px.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1, max_x - min_x)
        span_y = max(1, max_y - min_y)
        margin = 36

        def sp(name):
            px, py = node_px[name]
            nx = ox + margin + (px - min_x) / span_x * (pw - 2 * margin)
            ny = oy + margin + (py - min_y) / span_y * (ph - 2 * margin)
            return (int(nx), int(ny))

        # roads
        drawn = set()
        for (a, b) in m['road_pairs']:
            key = tuple(sorted([a, b]))
            if key in drawn:
                continue
            drawn.add(key)
            pygame.draw.line(surf, ROAD_C, sp(a), sp(b), 6)

        # intersections
        for iid in m['intersection_nodes']:
            cx, cy = sp(iid)
            pygame.draw.rect(surf, INT_C, (cx - 8, cy - 8, 16, 16))
            pygame.draw.rect(surf, GRAY,  (cx - 8, cy - 8, 16, 16), 1)

        # boundary zones
        font_tiny = pygame.font.Font(None, 18)
        for zone in m['boundary_zones']:
            cx, cy = sp(zone)
            pygame.draw.circle(surf, GRAY, (cx, cy), 4)
            _text(surf, font_tiny, zone, cx, cy - 10, TEXT_DIM, anchor='center')

        # map name centred below preview
        _text(surf, self.font, m['name'], ox + pw // 2, oy + ph + 8, ACCENT, anchor='midtop')
        n_int = len(m['intersection_nodes'])
        n_zon = len(m['boundary_zones'])
        _text(surf, self.font_sm, f'{n_int} intersections · {n_zon} entry zones',
              ox + pw // 2, oy + ph + 34, TEXT_DIM, anchor='midtop')

    @property
    def map_name(self):
        return MAP_ORDER[self.map_idx]

    @property
    def scenario(self):
        return SCENARIOS_LIST[self.scenario_idx]


# ──────────────────────────────────────────────────────────────────────
# RUNNING screen
# ──────────────────────────────────────────────────────────────────────

class RunningScreen:
    def __init__(self, engine, font, font_sm, font_lg, car_images):
        self.engine       = engine
        self.font         = font
        self.font_sm      = font_sm
        self.font_lg      = font_lg
        self.car_images   = car_images
        self.paused        = False
        self._spd_levels   = [0.25, 0.5, 1, 2, 3, 4, 5, 6, 8, 10]
        self._spd_idx      = 2      # default: 1× (index 2)
        self._step_acc     = 0.0
        self.iid_list      = sorted(engine.signals.signals.keys())
        self.selected_idx  = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            best_iid, best_d = None, float('inf')
            for iid in self.iid_list:
                cx, cy = self.engine.network.node_pixels[iid]
                d = (mx - cx) ** 2 + (my - cy) ** 2
                if d < best_d:
                    best_d, best_iid = d, iid
            if best_iid and best_d < (INTERSECTION_HALF_PX * 4) ** 2:
                self.selected_idx = self.iid_list.index(best_iid)
            return

        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()
        if k == pygame.K_p:
            self.paused = not self.paused
        if k in (pygame.K_EQUALS, pygame.K_KP_PLUS) or event.unicode in ('+', '='):
            self._spd_idx = min(self._spd_idx + 1, len(self._spd_levels) - 1)
        if k in (pygame.K_MINUS, pygame.K_KP_MINUS) or event.unicode == '-':
            self._spd_idx = max(self._spd_idx - 1, 0)
        if k == pygame.K_TAB and self.iid_list:
            self.selected_idx = (self.selected_idx + 1) % len(self.iid_list)
        _NUM_KEYS = [pygame.K_1, pygame.K_2, pygame.K_3,
                     pygame.K_4, pygame.K_5, pygame.K_6]
        for i, nk in enumerate(_NUM_KEYS):
            if k == nk and i < len(self.iid_list):
                self.selected_idx = i
        if self.iid_list:
            sel = self.iid_list[self.selected_idx]
            if k == pygame.K_n:
                self.engine.signals.signals[sel].force_green('NS')
            if k == pygame.K_e:
                self.engine.signals.signals[sel].force_green('EW')

    def update(self):
        if self.paused or self.engine.done:
            return
        self._step_acc += self._spd_levels[self._spd_idx]
        while self._step_acc >= 1.0:
            self._step_acc -= 1.0
            self.engine.step()
            if self.engine.done:
                self._step_acc = 0.0
                break

    def draw(self, surf):
        surf.fill(UI_BG)
        sel_iid = self.iid_list[self.selected_idx] if self.iid_list else None
        _draw_network(surf, self.engine.network, self.engine.signals, self.font_sm, sel_iid)
        _draw_vehicles(surf, self.engine.active_vehicles(), self.car_images)
        self._draw_hud(surf)

    def _draw_hud(self, surf):
        hx, hy = SCREEN_W - 212, 8
        hw, hh = 200, SCREEN_H - 16
        pygame.draw.rect(surf, UI_PANEL, (hx, hy, hw, hh), border_radius=6)
        pygame.draw.rect(surf, GRAY,     (hx, hy, hw, hh), 1, border_radius=6)

        y = hy + 10
        _text(surf, self.font_lg, 'HUD', hx + hw // 2, y, ACCENT, anchor='midtop')
        y += 32

        # Time bar
        elapsed = self.engine.sim_time
        _text(surf, self.font_sm, f'Time  {elapsed:.1f} / {HORIZON:.0f} s', hx + 8, y, TEXT_C)
        y += 18
        _bar(surf, hx + 8, y, hw - 16, 7, elapsed, HORIZON, ACCENT)
        y += 16

        if self.paused:
            _text(surf, self.font, '[ PAUSED ]', hx + hw // 2, y, SIG_YEL, anchor='midtop')
        else:
            spd = self._spd_levels[self._spd_idx]
            spd_lbl = f'Speed ×{int(spd)}' if spd >= 1 else f'Speed ×{spd}'
            spd_col = SIG_GRN if spd > 1 else (TEXT_DIM if spd == 1 else SIG_YEL)
            _text(surf, self.font_sm, spd_lbl, hx + 8, y, spd_col)
        y += 24

        # Vehicle counts
        pygame.draw.line(surf, DARK_GRAY, (hx + 6, y), (hx + hw - 6, y))
        y += 6
        cts = self.engine.counts()
        for label, val, col in [
            ('Total',     cts['total'],   TEXT_C),
            ('Active',    cts['active'],  SIG_GRN),
            ('Pending',   cts['pending'], TEXT_DIM),
            ('Completed', cts['done'],    ACCENT),
        ]:
            _text(surf, self.font_sm, label,    hx + 8,       y, TEXT_DIM)
            _text(surf, self.font,    str(val),  hx + hw - 8,  y, col, anchor='topright')
            y += 20

        # Signals
        pygame.draw.line(surf, DARK_GRAY, (hx + 6, y + 3), (hx + hw - 6, y + 3))
        y += 12
        _text(surf, self.font_sm, 'Signals', hx + 8, y, TEXT_DIM)
        y += 18
        for iid, sig in self.engine.signals.signals.items():
            ph  = sig.active_phase
            col = SIG_GRN if 'GREEN' in ph else (SIG_YEL if 'YELLOW' in ph else SIG_RED)
            _text(surf, self.font_sm, f'{iid} {ph[:2]} {sig.time_remaining:.0f}s',
                  hx + 8, y, col)
            y += 18

        # Selected intersection control panel
        pygame.draw.line(surf, DARK_GRAY, (hx + 6, y + 3), (hx + hw - 6, y + 3))
        y += 10
        if self.iid_list:
            sel_iid = self.iid_list[self.selected_idx]
            sig     = self.engine.signals.signals[sel_iid]
            ph      = sig.active_phase
            sig_col = SIG_GRN if 'GREEN' in ph else (SIG_YEL if 'YELLOW' in ph else SIG_RED)
            idx_num = self.selected_idx + 1
            _text(surf, self.font_sm,
                  f'Selected [{idx_num}]: {sel_iid}', hx + 8, y, ACCENT)
            y += 18
            _text(surf, self.font_sm, ph,                       hx + 8,       y, sig_col)
            _text(surf, self.font_sm, f'{sig.time_remaining:.0f}s',
                  hx + hw - 8, y, sig_col, anchor='topright')
            y += 18
            for seg in self.engine.network.segments.values():
                if seg.enters_intersection == sel_iid:
                    n     = len(seg.vehicles)
                    q_col = SIG_RED if n >= 5 else (SIG_YEL if n >= 2 else TEXT_C)
                    _text(surf, self.font_sm, f'  {seg.from_node}: {n}', hx + 8, y, q_col)
                    y += 15
            y += 4

        # Controls
        pygame.draw.line(surf, DARK_GRAY, (hx + 6, y + 3), (hx + hw - 6, y + 3))
        y += 10
        for hint in ['Click / 1-6: select', 'Tab: cycle intersect.',
                     'N: force NS green', 'E: force EW green',
                     'P: pause / resume', '+/−: speed']:
            _text(surf, self.font_sm, hint, hx + 8, y, TEXT_DIM)
            y += 15


# ──────────────────────────────────────────────────────────────────────
# Results-screen network snapshot (queue overlay)
# ──────────────────────────────────────────────────────────────────────

def _draw_results_network(surf, font_sm, network, queue_stats, bottleneck, ox, oy, pw, ph):
    """
    Mini network map for the Results screen.
    Intersection boxes are coloured green / yellow / red by residual queue size.
    Queue count is shown below each box; bottleneck gets a red outline.
    """
    # Leave room at top for 2-line title, at bottom for legend
    TITLE_H  = 34
    LEGEND_H = 22

    pygame.draw.rect(surf, UI_PANEL, (ox, oy, pw, ph), border_radius=6)
    pygame.draw.rect(surf, GRAY,     (ox, oy, pw, ph), 1, border_radius=6)

    # Two-line title
    _text(surf, font_sm, 'Residual queues at end of simulation',
          ox + pw // 2, oy + 4, TEXT_C, anchor='midtop')
    _text(surf, font_sm, 'Vehicles still waiting at each intersection when time ran out',
          ox + pw // 2, oy + 19, TEXT_DIM, anchor='midtop')

    node_px = network.node_pixels
    xs = [p[0] for p in node_px.values()]
    ys = [p[1] for p in node_px.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)

    # Map area sits between title and legend
    margin  = 32
    map_y0  = oy + TITLE_H
    map_h   = ph - TITLE_H - LEGEND_H
    map_w   = pw

    def sp(name):
        px, py = node_px[name]
        nx = ox + margin + (px - min_x) / span_x * (map_w - 2 * margin)
        ny = map_y0 + margin + (py - min_y) / span_y * (map_h - 2 * margin)
        return (int(nx), int(ny))

    # Roads
    drawn = set()
    for (a, b) in network.road_pairs:
        key = tuple(sorted([a, b]))
        if key in drawn:
            continue
        drawn.add(key)
        pygame.draw.line(surf, ROAD_C, sp(a), sp(b), 5)

    # Boundary zones (small dots)
    for zone in network.boundary_zones:
        cx, cy = sp(zone)
        pygame.draw.circle(surf, GRAY, (cx, cy), 4)

    # Intersection boxes — coloured by queue status
    BOX      = 13
    font_num = pygame.font.SysFont(None, 22, bold=True)
    for iid in sorted(network.intersection_nodes):
        cx, cy = sp(iid)
        q      = queue_stats.get(iid, 0)
        is_bot = (iid == bottleneck and q > 0)
        fill   = SIG_RED if is_bot else (SIG_YEL if q > 0 else SIG_GRN)
        pygame.draw.rect(surf, fill, (cx - BOX, cy - BOX, BOX * 2, BOX * 2))
        pygame.draw.rect(surf, GRAY, (cx - BOX, cy - BOX, BOX * 2, BOX * 2), 1)
        if is_bot:
            pygame.draw.rect(surf, SIG_RED,
                             (cx - BOX - 3, cy - BOX - 3, BOX*2+6, BOX*2+6), 2)
        # IID label above the box
        _text(surf, font_sm, iid, cx, cy - BOX - 14, TEXT_C, anchor='center')
        # Queue count centred inside the box, bold
        _text(surf, font_num, str(q), cx, cy, BLACK, anchor='center')

    # Legend — centred along the bottom of the panel
    legend_y  = oy + ph - LEGEND_H + 4
    items     = [(SIG_GRN, 'clear'), (SIG_YEL, 'queued'), (SIG_RED, 'bottleneck')]
    item_w    = 90
    leg_start = ox + (pw - len(items) * item_w) // 2
    for i, (col, lbl) in enumerate(items):
        lx = leg_start + i * item_w
        pygame.draw.rect(surf, col, (lx, legend_y + 2, 9, 9))
        _text(surf, font_sm, lbl, lx + 13, legend_y + 1, TEXT_DIM)


# ──────────────────────────────────────────────────────────────────────
# Performance boxplots helper
# ──────────────────────────────────────────────────────────────────────

def _draw_boxplots(surf, font, font_sm, past_runs, current_idx, ox, oy, pw, ph):
    """
    Three vertical boxplots (throughput %, equity %, avg delay) with the
    current run highlighted and its percentile rank shown.
    """
    pygame.draw.rect(surf, UI_PANEL, (ox, oy, pw, ph), border_radius=6)
    pygame.draw.rect(surf, GRAY,     (ox, oy, pw, ph), 1, border_radius=6)

    _text(surf, font_sm, 'How did you do?  (same map & scenario)',
          ox + pw // 2, oy + 8, TEXT_DIM, anchor='midtop')

    n = len(past_runs)
    if n < 2:
        msg = 'Finish another run to unlock the comparison chart.'
        _text(surf, font_sm, msg, ox + pw // 2, oy + ph // 2, TEXT_DIM, anchor='center')
        return

    _text(surf, font_sm, f'{n} runs recorded',
          ox + pw - 10, oy + 8, TEXT_DIM, anchor='topright')

    cur = past_runs[current_idx]

    # (label, [all values], current value, unit, higher_is_better)
    specs = [
        ('Throughput', [r['throughput'] * 100 for r in past_runs],
         cur['throughput'] * 100, '%',  True),
        ('Equity',     [r['equity']     * 100 for r in past_runs],
         cur['equity']     * 100, '%',  True),
        ('Avg Delay',  [r['avg_delay']         for r in past_runs],
         cur['avg_delay'],         's', False),
    ]

    PAD_TOP = 38
    PAD_BOT = 62
    PAD_LR  = 44   # wider left margin for axis labels
    plot_y0 = oy + PAD_TOP
    plot_y1 = oy + ph - PAD_BOT
    plot_h  = plot_y1 - plot_y0
    col_w   = (pw - 2 * PAD_LR) // 3
    box_w   = max(30, col_w // 3)

    # Fixed 0-100 scale shared by all three plots
    def to_y(v):
        return int(plot_y1 - max(0.0, min(100.0, v)) / 100.0 * plot_h)

    # Horizontal gridlines at 0, 20, 40, 60, 80, 100 — drawn once across all columns
    grid_x0 = ox + PAD_LR
    grid_x1 = ox + pw - PAD_LR
    for gv in range(0, 101, 20):
        gy = to_y(gv)
        pygame.draw.line(surf, DARK_GRAY, (grid_x0, gy), (grid_x1, gy), 1)
        _text(surf, font_sm, str(gv), grid_x0 - 4, gy, TEXT_DIM, anchor='midright')

    for col_i, (label, vals, cur_val, unit, higher_better) in enumerate(specs):
        cx = ox + PAD_LR + col_w * col_i + col_w // 2

        sv  = sorted(vals)
        nv  = len(sv)
        q1  = sv[max(0, nv // 4 - 1)]
        med = sv[nv // 2]
        q3  = sv[min(nv - 1, 3 * nv // 4)]

        # Whisker (data min → max, clamped to 0-100)
        pygame.draw.line(surf, DARK_GRAY, (cx, to_y(sv[0])), (cx, to_y(sv[-1])), 1)
        cap = max(4, box_w // 4)
        pygame.draw.line(surf, DARK_GRAY, (cx-cap, to_y(sv[0])),  (cx+cap, to_y(sv[0])),  1)
        pygame.draw.line(surf, DARK_GRAY, (cx-cap, to_y(sv[-1])), (cx+cap, to_y(sv[-1])), 1)

        # IQR box
        iq_top = to_y(q3)
        iq_bot = to_y(q1)
        pygame.draw.rect(surf, HIGHLIGHT, (cx - box_w//2, iq_top, box_w, iq_bot - iq_top))
        pygame.draw.rect(surf, GRAY,      (cx - box_w//2, iq_top, box_w, iq_bot - iq_top), 1)

        # Median line
        pygame.draw.line(surf, WHITE,
                         (cx - box_w//2, to_y(med)),
                         (cx + box_w//2, to_y(med)), 2)

        # Current run dot
        cur_y_px = to_y(cur_val)
        pygame.draw.circle(surf, UI_BG,  (cx, cur_y_px), 7)
        pygame.draw.circle(surf, WHITE,  (cx, cur_y_px), 6)
        pygame.draw.circle(surf, ACCENT, (cx, cur_y_px), 6, 2)

        # Percentile rank
        n_below  = sum(1 for v in vals if v < cur_val)
        pct_rank = 100 * n_below // nv
        pct_good = pct_rank if higher_better else (100 - pct_rank)
        pct_col  = SIG_GRN if pct_good >= 70 else (SIG_YEL if pct_good >= 40 else SIG_RED)
        pct_lbl  = f'top {100 - pct_good}%' if pct_good >= 50 else f'bottom {pct_good}%'

        # Labels below the plot
        _text(surf, font,    label,                  cx, plot_y1 + 8,  TEXT_DIM, anchor='midtop')
        _text(surf, font_sm, f'{cur_val:.1f}{unit}', cx, plot_y1 + 26, WHITE,    anchor='midtop')
        _text(surf, font_sm, pct_lbl,                cx, plot_y1 + 42, pct_col,  anchor='midtop')


# ──────────────────────────────────────────────────────────────────────
# RESULTS screen
# ──────────────────────────────────────────────────────────────────────

class ResultsScreen:
    def __init__(self, metrics, past_runs, network, font, font_sm, font_lg):
        self.m         = metrics
        self.past_runs = past_runs
        self.network   = network
        self.font      = font
        self.font_sm   = font_sm
        self.font_lg   = font_lg
        self.restart   = False

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

        _text(surf, self.font_lg, 'RESULTS', SCREEN_W // 2, 20, ACCENT, anchor='midtop')

        # ── KPI boxes (full width) ──────────────────────────────────────
        kpi_y = 66
        kpi_w = 240
        kpi_h = 76
        gap   = 14

        def kpi(label, val_str, col, x, y):
            pygame.draw.rect(surf, UI_PANEL, (x, y, kpi_w, kpi_h), border_radius=8)
            pygame.draw.rect(surf, col,      (x, y, kpi_w, kpi_h), 1, border_radius=8)
            _text(surf, self.font_sm, label,   x + kpi_w // 2, y + 8,  TEXT_DIM, anchor='midtop')
            _text(surf, self.font_lg, val_str, x + kpi_w // 2, y + 30, col,      anchor='midtop')

        tp_pct = int(m['throughput'] * 100)
        eq_pct = int(m['equity'] * 100)
        t_col  = SIG_GRN if tp_pct >= 70 else (SIG_YEL if tp_pct >= 40 else SIG_RED)
        e_col  = SIG_GRN if eq_pct >= 70 else (SIG_YEL if eq_pct >= 40 else SIG_RED)

        total_w = 4 * kpi_w + 3 * gap
        kpi_x0  = (SCREEN_W - total_w) // 2

        kpi('Throughput', f'{tp_pct}%',                        t_col,  kpi_x0,                    kpi_y)
        kpi('Equity',     f'{eq_pct}%',                        e_col,  kpi_x0 +   kpi_w + gap,    kpi_y)
        kpi('Avg Delay',  f'{m["avg_delay"]:.1f} s',           ACCENT, kpi_x0 + 2*(kpi_w + gap),  kpi_y)
        kpi('Trips Done', f'{m["completed"]} / {m["total"]}',  TEXT_C, kpi_x0 + 3*(kpi_w + gap),  kpi_y)

        content_y = kpi_y + kpi_h + 18
        content_h = SCREEN_H - content_y - 36

        # ── Left column: network snapshot + per-OD bars ────────────────
        LEFT_X   = 30
        LEFT_W   = 470
        NET_H    = 210    # height of the network snapshot panel
        y        = content_y

        # Network snapshot with residual queues overlaid
        _draw_results_network(surf, self.font_sm, self.network,
                              m['queue_stats'], m['bottleneck'],
                              LEFT_X, y, LEFT_W, NET_H)
        y += NET_H + 12

        # Worst per-OD delay bars
        _text(surf, self.font, 'Worst per-OD delays:', LEFT_X, y, TEXT_C)
        y += 22
        od_sorted = sorted(
            [(k, sum(v) / len(v)) for k, v in m['od_delays'].items() if v],
            key=lambda x: -x[1],
        )[:7]
        bar_x = LEFT_X + 90
        bar_w = LEFT_W - 90 - 52
        for (o, d), avg in od_sorted:
            bar_val = min(avg, 60.0)
            col     = _lerp_color(SIG_GRN, SIG_RED, bar_val / 60.0)
            _text(surf, self.font_sm, f'{o}→{d}', LEFT_X, y, TEXT_DIM)
            _bar(surf, bar_x, y + 2, bar_w, 13, bar_val, 60.0, col)
            _text(surf, self.font_sm, f'{avg:.0f}s', bar_x + bar_w + 6, y, TEXT_C)
            y += 20
            if y > content_y + content_h:
                break

        # ── Right column: performance boxplots ─────────────────────────
        RIGHT_X = LEFT_X + LEFT_W + 20
        RIGHT_W = SCREEN_W - RIGHT_X - 16
        _draw_boxplots(surf, self.font, self.font_sm,
                       self.past_runs, len(self.past_runs) - 1,
                       RIGHT_X, content_y, RIGHT_W, content_h)

        # ── Footer ──────────────────────────────────────────────────────
        _text(surf, self.font, 'R / ENTER → play again    ESC → quit',
              SCREEN_W // 2, SCREEN_H - 28, TEXT_DIM, anchor='midtop')


# ──────────────────────────────────────────────────────────────────────
# Main application loop
# ──────────────────────────────────────────────────────────────────────

def run():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption('Adaptive Traffic Control — Serious Game')
    clock = pygame.time.Clock()

    font_lg = pygame.font.Font(None, 44)
    font    = pygame.font.Font(None, 28)
    font_sm = pygame.font.Font(None, 20)

    car_images = _load_car_images()

    while True:
        # ── PRE-RUN ──────────────────────────────────────────────────
        pre = PreRunScreen(font, font_sm, font_lg)
        while not pre.done:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                pre.handle_event(ev)
            pre.draw(screen)
            pygame.display.flip()

        # ── BUILD ENGINE ─────────────────────────────────────────────
        engine  = SimulationEngine(map_name=pre.map_name, scenario=pre.scenario)
        running = RunningScreen(engine, font, font_sm, font_lg, car_images)

        # ── RUNNING ──────────────────────────────────────────────────
        while not engine.done:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                running.handle_event(ev)
            running.update()
            running.draw(screen)
            pygame.display.flip()

        running.draw(screen)
        pygame.display.flip()
        pygame.time.wait(500)

        # ── RESULTS ──────────────────────────────────────────────────
        past_runs = save_run(pre.map_name, pre.scenario, engine.metrics)
        results   = ResultsScreen(engine.metrics, past_runs, engine.network,
                                  font, font_sm, font_lg)
        while not results.restart:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                results.handle_event(ev)
            results.draw(screen)
            pygame.display.flip()
