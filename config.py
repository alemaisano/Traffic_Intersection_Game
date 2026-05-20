# Simulation timing
DT = 0.1
HORIZON = 60.0
MAX_STEPS = int(HORIZON / DT)

# Display
SCREEN_W = 1400
SCREEN_H = 800
FPS = 30
STEPS_PER_FRAME = 1   # simulation steps per rendered frame (3x real-time at 30fps)

# Network geometry
PIXELS_PER_METER = 8.0
LANE_OFFSET_PX = 9          # pixels from road centre to lane centre
INTERSECTION_HALF_PX = 48   # half-size of intersection box in pixels
INTERSECTION_HALF_M = INTERSECTION_HALF_PX / PIXELS_PER_METER

# Node pixel centres
NODE_PIXELS = {
    'I1': (350,  200),
    'I2': (1050, 200),
    'I3': (350,  600),
    'I4': (1050, 600),
    'TL': (350,  35),
    'TR': (1050, 35),
    'LT': (35,   200),
    'LB': (35,   600),
    'RT': (1365, 200),
    'RB': (1365, 600),
    'BL': (350,  765),
    'BR': (1050, 765),
}

INTERSECTION_NODES = {'I1', 'I2', 'I3', 'I4'}
BOUNDARY_ZONES = ['TL', 'TR', 'LT', 'LB', 'RT', 'RB', 'BL', 'BR']

# Undirected road pairs (each becomes 2 directed segments)
ROAD_PAIRS = [
    ('TL', 'I1'), ('TR', 'I2'),
    ('LT', 'I1'), ('LB', 'I3'),
    ('RT', 'I2'), ('RB', 'I4'),
    ('BL', 'I3'), ('BR', 'I4'),
    ('I1', 'I2'), ('I1', 'I3'),
    ('I2', 'I4'), ('I3', 'I4'),
]

# Vehicle gaps (metres)
STOPPING_GAP = 2.5
MOVING_GAP   = 3.0

# Signal defaults (seconds)
DEFAULT_NS_GREEN = 15
DEFAULT_EW_GREEN = 15
DEFAULT_YELLOW   = 3
MIN_GREEN        = 5
MAX_GREEN        = 55
MAX_CYCLE        = 60

# Vehicle parameters: max_speed m/s, accel m/s², decel m/s², length m
VEHICLE_PARAMS = {
    'car':   {'max_speed': 12.0, 'accel': 3.0, 'decel': 5.0, 'length': 4.5,
              'color': (100, 149, 237), 'weight': 1},
    'bike':  {'max_speed':  8.0, 'accel': 2.5, 'decel': 4.0, 'length': 2.0,
              'color': (144, 238, 144), 'weight': 1},
    'truck': {'max_speed':  7.0, 'accel': 1.0, 'decel': 2.5, 'length': 8.0,
              'color': (210, 105,  30), 'weight': 2},
    'bus':   {'max_speed':  9.0, 'accel': 1.5, 'decel': 3.0, 'length': 10.0,
              'color': (255, 165,   0), 'weight': 3},
}

VEHICLE_MIX = [('car', 0.60), ('bike', 0.20), ('truck', 0.10), ('bus', 0.10)]

SCENARIOS = {
    'light':    {'lam': 0.3},
    'balanced': {'lam': 0.7},
    'peak':     {'lam': 1.4},
}

# Colours
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
GRAY       = (120, 120, 120)
DARK_GRAY  = ( 40,  40,  40)
ROAD_C     = ( 55,  55,  55)
INT_C      = ( 72,  72,  72)
SIG_RED    = (200,  40,  40)
SIG_YEL    = (220, 200,   0)
SIG_GRN    = ( 40, 180,  40)
UI_BG      = ( 18,  18,  28)
UI_PANEL   = ( 30,  30,  46)
HIGHLIGHT  = ( 70,  70, 130)
TEXT_C     = (200, 200, 200)
TEXT_DIM   = (120, 120, 120)
ACCENT     = ( 80, 160, 220)
