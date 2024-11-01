# parameters.py
# Timing parameters
TR = 1.5  # TR (Repetition Time) in seconds
TRs_per_trial = 6
TRs_dummy_scans = 5  
TRs_rest = 6
TRs_instruction = 2 

# Experiment setup
blocks = 4  # Number of blocks
trials_per_block = 7  # Trials per block - this should be linked to the number of conditions (below)

# Condition definitions (names and codes)
cond_names = ["LEFT ELBOW", "RIGHT ELBOW", "LEFT HAND", "RIGHT HAND", "LEFT FOOT", "RIGHT FOOT", "TONGUE"]
cond_codes = [1, 2, 3, 4, 6, 7, 8] #we save 5 for trigger, but you can use whatever you like

# Text settings (increase if text remains small with height units)
instruction_text_size = 0.08  # 5% of window height
trial_text_size = 0.09        # 8% of window height
fixation_text_size = 0.11      # 10% of window height
countdown_image_size = (0.4, 0.4)  # Set countdown image size to half of the original for display (adjust as needed)
countdown_image_position = (0, 0.2)  # Position offset for images, e.g., (0, 0.2) moves it 20% up the screen
# Colors
background_color = 'black'  # Use 'black' for a black background
text_color = 'yellow'

# Monitor settings
full_screen = True

# Trigger settings
trigger_input_method = 'key'  # Can be 'key', 'parallel', or 'serial'
trigger_value = '5'  # Trigger key or value
port_address = None  # For parallel input, specify the port address
serial_port = None  # For serial input, specify the serial port