"""
Experiment parameters for BodyLocaliser.

Edit this file to configure timing, conditions, display, and trigger settings.
All timing values are specified in units of TRs (scanner repetition times).
"""

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
TR = 1.5                # Repetition Time in seconds
TRs_per_trial = 6       # TRs per motor trial  (6 x 1.5 = 9 s)
TRs_dummy_scans = 0     # TRs of dummy scans before experiment starts
TRs_rest = 6            # TRs per rest period   (6 x 1.5 = 9 s)
TRs_final_rest = 10     # TRs of rest after the last block (10 x 1.5 = 15 s)
TRs_instruction = 2     # TRs for initial instruction screen

# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------
# Each condition is presented once per block, in the run order chosen at the
# start: a preset OpenRecon order from src/run_orders.py, or a balanced random
# order. The names must match those in src/run_orders.py: to use different body
# regions, edit this list, rerun python3 tools/make_run_orders.py, and give the
# OpenRecon container the rebuilt file. See "Different body regions" in README.md.
COND_NAMES = [
    "LEFT ELBOW", "RIGHT ELBOW",
    "LEFT HAND",  "RIGHT HAND",
    "LEFT FOOT",  "RIGHT FOOT",
    "TONGUE",
]

# ---------------------------------------------------------------------------
# Experiment structure
# ---------------------------------------------------------------------------
BLOCKS = 4                  # 1 to 8; 4 recommended. Must be a block count in src/run_orders.py
# A TRs_rest rest follows this trial in every block. None centres it on the movements,
# ceil(len(COND_NAMES) / 2), which is 4 of the 7 below, so it follows if you change them.
# Set a trial number to place it yourself, or 0 for no rest inside a block.
MID_BLOCK_REST_AFTER = None

# ---------------------------------------------------------------------------
# Countdown images
# ---------------------------------------------------------------------------
# The assets/images/ folder must contain files named 1.png .. N.png.
# This also sets the movement pace: one image per movement, so the trial length
# divided by this number is the interval asked for between movements. TR and
# TRs_per_trial change it too, so read the pace off python3 src/design.py rather
# than assuming it. If you change the number, add or remove the matching files.
NUM_COUNTDOWN_IMAGES = 12

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
INSTRUCTION_TEXT_SIZE = 0.08   # 8% of window height  (instructions, waiting screen)
TRIAL_TEXT_SIZE = 0.09         # 9% of window height  (the MOVE <body part> cue)
FIXATION_TEXT_SIZE = 0.11      # 11% of window height
COUNTDOWN_IMAGE_SIZE = (0.4, 0.4)
COUNTDOWN_IMAGE_POSITION = (0, 0.2)  # offset upward from centre

BACKGROUND_COLOR = "black"
TEXT_COLOR = "yellow"

FULL_SCREEN = True

# ---------------------------------------------------------------------------
# Scanner trigger
# ---------------------------------------------------------------------------
# input_method: 'key' (keyboard, for testing), 'parallel', or 'serial'
TRIGGER_INPUT_METHOD = "key"
TRIGGER_VALUE = "5"            # key or byte value to wait for
PORT_ADDRESS = None            # hex address for parallel port (e.g. 0x0378)
SERIAL_PORT = None             # device path for serial port (e.g. '/dev/ttyUSB0')
