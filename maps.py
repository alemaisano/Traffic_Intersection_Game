"""
maps.py  –  Network topology definitions.

Each entry:
  name / description
  node_pixels          {node_id: (x, y)} – pixel centres on 1100×680 screen
  intersection_nodes   set  – which nodes have signal control
  boundary_zones       list – ordered entry/exit zones (form the OD matrix)
  road_pairs           list – undirected edges (each yields 2 directed segments)
  signal_config        {iid: {start_phase, start_offset}} – stagger to avoid
                       all intersections switching simultaneously
"""

# ── 1. Boulevard ────────────────────────────────────────────────────────
# Two intersections on a shared arterial.
#
#     TL        TR
#      |         |
#  LT--I1--------I2--RT
#      |         |
#     BL        BR
_BOULEVARD = {
    'name':        'Boulevard',
    'description': 'Two lights on an arterial. Coordinate the green wave.',
    'node_pixels': {
        'I1': (255, 330), 'I2': (635, 330),
        'TL': (255,  28), 'TR': (635,  28),
        'BL': (255, 645), 'BR': (635, 645),
        'LT': ( 28, 330), 'RT': (860, 330),
    },
    'intersection_nodes': {'I1', 'I2'},
    'boundary_zones':     ['TL', 'TR', 'BL', 'BR', 'LT', 'RT'],
    'road_pairs': [
        ('TL', 'I1'), ('BL', 'I1'), ('LT', 'I1'), ('I1', 'I2'),
        ('TR', 'I2'), ('BR', 'I2'), ('RT', 'I2'),
    ],
    'signal_config': {
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
    },
}

# ── 2. Main Street ──────────────────────────────────────────────────────
# Three intersections in a line.  Optimise the green wave.
#
#   TL     TM      TR
#    |      |       |
# LT-I1----I2------I3-RT
#    |      |       |
#   BL     BM      BR
_MAIN_STREET = {
    'name':        'Main Street',
    'description': 'Three lights in a row. Time the green wave.',
    'node_pixels': {
        'I1': (155, 330), 'I2': (445, 330), 'I3': (735, 330),
        'TL': (155,  28), 'TM': (445,  28), 'TR': (735,  28),
        'BL': (155, 645), 'BM': (445, 645), 'BR': (735, 645),
        'LT': ( 28, 330), 'RT': (860, 330),
    },
    'intersection_nodes': {'I1', 'I2', 'I3'},
    'boundary_zones':     ['TL', 'TM', 'TR', 'BL', 'BM', 'BR', 'LT', 'RT'],
    'road_pairs': [
        ('TL', 'I1'), ('BL', 'I1'), ('LT', 'I1'), ('I1', 'I2'),
        ('TM', 'I2'), ('BM', 'I2'), ('I2', 'I3'),
        ('TR', 'I3'), ('BR', 'I3'), ('RT', 'I3'),
    ],
    'signal_config': {
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
        'I3': {'start_phase': 'NS', 'start_offset': 10.0},
    },
}

# ── 3. L-Junction ───────────────────────────────────────────────────────
# Three intersections in an L-shape.  Asymmetric demand balance.
#
#   TL        TR
#    |         |
# LT-I1--------I2-RT
#    |          |
#   LB         RS
#    |
#   I3
#    |
#   BL
_L_JUNCTION = {
    'name':        'L-Junction',
    'description': 'Three lights in an L. Balance skewed demand.',
    'node_pixels': {
        'I1': (255, 200), 'I2': (615, 200), 'I3': (255, 490),
        'TL': (255,  28), 'TR': (615,  28),
        'LT': ( 28, 200), 'LB': ( 28, 490),
        'RT': (860, 200),
        'RS': (615, 490),
        'BL': (255, 645),
    },
    'intersection_nodes': {'I1', 'I2', 'I3'},
    'boundary_zones':     ['TL', 'TR', 'LT', 'LB', 'RT', 'RS', 'BL'],
    'road_pairs': [
        ('TL', 'I1'), ('LT', 'I1'), ('I1', 'I2'), ('I1', 'I3'),
        ('TR', 'I2'), ('RT', 'I2'), ('RS', 'I2'),
        ('LB', 'I3'), ('BL', 'I3'),
    ],
    'signal_config': {
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
        'I3': {'start_phase': 'NS', 'start_offset':  5.0},
    },
}

# ── 4. T-Cross ──────────────────────────────────────────────────────────
# Four intersections: three on a horizontal artery + one on a southern arm.
# I2 is a triple-connection bottleneck (three other intersections + TC above).
#
#   TL   TC   TR
#    |    |    |
# LT-I1--I2--I3-RT
#        |
#    LB-I4-RB
#        |
#       BC
_T_CROSS = {
    'name':        'T-Cross',
    'description': 'Four lights: I2 is the hub. Manage its competing flows.',
    'node_pixels': {
        'I1': (175, 250), 'I2': (445, 250), 'I3': (715, 250), 'I4': (445, 490),
        'TL': (175,  28), 'TC': (445,  28), 'TR': (715,  28),
        'LT': ( 28, 250), 'RT': (860, 250),
        'LB': ( 28, 490), 'RB': (860, 490),
        'BC': (445, 645),
    },
    'intersection_nodes': {'I1', 'I2', 'I3', 'I4'},
    'boundary_zones':     ['TL', 'TC', 'TR', 'LT', 'RT', 'LB', 'RB', 'BC'],
    'road_pairs': [
        ('TL', 'I1'), ('LT', 'I1'), ('I1', 'I2'),
        ('TC', 'I2'), ('I2', 'I3'), ('I2', 'I4'),
        ('TR', 'I3'), ('RT', 'I3'),
        ('LB', 'I4'), ('RB', 'I4'), ('BC', 'I4'),
    ],
    'signal_config': {
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
        'I3': {'start_phase': 'NS', 'start_offset':  0.0},
        'I4': {'start_phase': 'NS', 'start_offset': 10.0},
    },
}

# ── 5. Downtown Grid ────────────────────────────────────────────────────
# Full 2×2 grid.
#
#   TL        TR
#    |         |
# LT-I1--------I2-RT
#    |          |
# LB-I3--------I4-RB
#    |          |
#   BL        BR
_DOWNTOWN = {
    'name':        'Downtown Grid',
    'description': '2×2 grid. Four intersections, eight entry points.',
    'node_pixels': {
        'I1': (255, 175), 'I2': (755, 175),
        'I3': (255, 490), 'I4': (755, 490),
        'TL': (255,  28), 'TR': (755,  28),
        'LT': ( 28, 175), 'LB': ( 28, 490),
        'RT': (860, 175), 'RB': (860, 490),
        'BL': (255, 645), 'BR': (755, 645),
    },
    'intersection_nodes': {'I1', 'I2', 'I3', 'I4'},
    'boundary_zones':     ['TL', 'TR', 'LT', 'LB', 'RT', 'RB', 'BL', 'BR'],
    'road_pairs': [
        ('TL', 'I1'), ('TR', 'I2'), ('LT', 'I1'), ('LB', 'I3'),
        ('RT', 'I2'), ('RB', 'I4'), ('BL', 'I3'), ('BR', 'I4'),
        ('I1', 'I2'), ('I1', 'I3'), ('I2', 'I4'), ('I3', 'I4'),
    ],
    'signal_config': {
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
        'I3': {'start_phase': 'EW', 'start_offset':  0.0},
        'I4': {'start_phase': 'NS', 'start_offset':  0.0},
    },
}

# ── 6. City Grid ────────────────────────────────────────────────────────
# 3×2 grid – six intersections, ten entry zones, the hardest map.
#
#   TL   TC   TR
#    |    |    |
# LT-I1--I2--I3-RT
#    |    |    |
# LB-I4--I5--I6-RB
#    |    |    |
#   BL   BC   BR
_CITY_GRID = {
    'name':        'City Grid',
    'description': '3×2 grid with six intersections. Maximum complexity.',
    'node_pixels': {
        'I1': (160, 175), 'I2': (440, 175), 'I3': (720, 175),
        'I4': (160, 490), 'I5': (440, 490), 'I6': (720, 490),
        'TL': (160,  28), 'TC': (440,  28), 'TR': (720,  28),
        'BL': (160, 645), 'BC': (440, 645), 'BR': (720, 645),
        'LT': ( 28, 175), 'LB': ( 28, 490),
        'RT': (860, 175), 'RB': (860, 490),
    },
    'intersection_nodes': {'I1', 'I2', 'I3', 'I4', 'I5', 'I6'},
    'boundary_zones':     ['TL', 'TC', 'TR', 'BL', 'BC', 'BR', 'LT', 'LB', 'RT', 'RB'],
    'road_pairs': [
        # external N
        ('TL', 'I1'), ('TC', 'I2'), ('TR', 'I3'),
        # external S
        ('BL', 'I4'), ('BC', 'I5'), ('BR', 'I6'),
        # external W
        ('LT', 'I1'), ('LB', 'I4'),
        # external E
        ('RT', 'I3'), ('RB', 'I6'),
        # internal horizontal
        ('I1', 'I2'), ('I2', 'I3'),
        ('I4', 'I5'), ('I5', 'I6'),
        # internal vertical
        ('I1', 'I4'), ('I2', 'I5'), ('I3', 'I6'),
    ],
    'signal_config': {
        # checkerboard phase stagger
        'I1': {'start_phase': 'NS', 'start_offset':  0.0},
        'I2': {'start_phase': 'EW', 'start_offset':  0.0},
        'I3': {'start_phase': 'NS', 'start_offset': 10.0},
        'I4': {'start_phase': 'EW', 'start_offset': 10.0},
        'I5': {'start_phase': 'NS', 'start_offset':  0.0},
        'I6': {'start_phase': 'EW', 'start_offset':  0.0},
    },
}

# ── Public API ──────────────────────────────────────────────────────────
MAPS = {
    'boulevard':   _BOULEVARD,
    'main_street': _MAIN_STREET,
    'l_junction':  _L_JUNCTION,
    't_cross':     _T_CROSS,
    'downtown':    _DOWNTOWN,
    'city_grid':   _CITY_GRID,
}

MAP_ORDER = ['boulevard', 'main_street', 'l_junction', 't_cross', 'downtown', 'city_grid']
