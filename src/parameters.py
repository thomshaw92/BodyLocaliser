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
TRs_instruction = 2     # TRs for initial instruction screen

# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------
# Each condition is presented once per block in a randomised order.
# cond_codes are written alongside onset files for analysis pipelines.
# Code 5 is reserved for the scanner trigger by convention.
COND_NAMES = [
    "LEFT ELBOW", "RIGHT ELBOW",
    "LEFT HAND",  "RIGHT HAND",
    "LEFT FOOT",  "RIGHT FOOT",
    "TONGUE",
]
COND_CODES = [1, 2, 3, 4, 6, 7, 8]

# ---------------------------------------------------------------------------
# Experiment structure
# ---------------------------------------------------------------------------
BLOCKS = 2
# Derived -- one trial per condition per block. Change COND_NAMES to adjust.
TRIALS_PER_BLOCK = len(COND_NAMES)

# ---------------------------------------------------------------------------
# Countdown images
# ---------------------------------------------------------------------------
# The images/ folder must contain files named 1.png .. N.png.
# If you change the number of images, update this constant and add/remove
# the corresponding files.
NUM_COUNTDOWN_IMAGES = 12

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
INSTRUCTION_TEXT_SIZE = 0.08   # 8% of window height
TRIAL_TEXT_SIZE = 0.09         # 9% of window height  (currently unused -- reserved)
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
