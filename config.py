# Simulation timing
DT = 0.1
HORIZON = 180.0          # 3 minutes
MAX_STEPS = int(HORIZON / DT)

# Display
SCREEN_W = 1100
SCREEN_H = 680
FPS = 30
STEPS_PER_FRAME = 1

# Network geometry
PIXELS_PER_METER = 8.0
LANE_OFFSET_PX   = 12          # pixels from road centre to lane centre
INTERSECTION_HALF_PX = 40      # half-size of intersection box in pixels
INTERSECTION_HALF_M  = INTERSECTION_HALF_PX / PIXELS_PER_METER

# Vehicle gaps (metres)
STOPPING_GAP = 2.5
MOVING_GAP   = 3.0

# Standard signal timing (seconds) – fixed, not player-editable
STANDARD_NS_GREEN = 20
STANDARD_EW_GREEN = 20
STANDARD_YELLOW   = 3

# Vehicle parameters: max_speed m/s, accel m/s², decel m/s², length m
# Only cars are used in this version.
VEHICLE_PARAMS = {
    'car': {'max_speed': 12.0, 'accel': 3.0, 'decel': 5.0, 'length': 4.5,
            'color': (100, 149, 237), 'weight': 1},
}

VEHICLE_MIX = [('car', 1.0)]

SCENARIOS = {
    'light':    {'lam': 2.0},
    'balanced': {'lam': 4.5},
    'peak':     {'lam': 9.0},
}

# Colours
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
GRAY       = (120, 120, 120)
DARK_GRAY  = ( 40,  40,  40)
ROAD_C     = ( 55,  55,  55)
CENTRE_C   = ( 90,  90,  90)   # road centre-line colour
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
