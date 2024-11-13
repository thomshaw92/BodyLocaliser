from psychopy import visual, core, event, gui, monitors
import os
from parameters import *  # Import all parameters from parameters.py
import logging
logging.basicConfig(level=logging.DEBUG)  # This sets the logging level to DEBUG

# Wait for trigger function
def wait_for_trigger(input_method='key', trigger_value='5', port_address=None, serial_port=None):
    """
    Waits for scanner trigger. Can use key, parallel, or serial input.
    """
    if input_method == 'key':
        print(f"Waiting for key press: {trigger_value}")
        event.waitKeys(keyList=[trigger_value])
        print("Trigger received (key press)")

    elif input_method == 'parallel':
        if port_address is None:
            raise ValueError("Port address must be provided for parallel input.")
        parallel_port = parallel.ParallelPort(address=port_address)
        print(f"Waiting for parallel port trigger at address {port_address}...")
        while True:
            if parallel_port.readPin(10):
                print("Trigger received (parallel port)")
                break
            core.wait(0.001)

    elif input_method == 'serial':
        if serial_port is None:
            raise ValueError("Serial port must be provided for serial input.")
        ser = serial.Serial(serial_port, 9600, timeout=1)
        print(f"Waiting for serial port trigger on {serial_port}...")
        while True:
            if ser.in_waiting > 0:
                signal = ser.read().decode('utf-8')
                if signal == trigger_value:
                    print("Trigger received (serial port)")
                    break
            core.wait(0.001)
    else:
        raise ValueError("Invalid input method. Choose 'key', 'parallel', or 'serial'.")

# Function to get subject info with validation and instructions
def get_subject_info():
    while True:
        # Create a custom dialog box
        info_dialog = gui.Dlg(title="Subject Information")
        info_dialog.addText("Instructions: If you want to quit the experiment at any time, press Ctrl+C or CMD+Q on Mac.")
        info_dialog.addField("Participant Initials: ")
        info_dialog.addField("Subject Number: ")
        info_dialog.addField("Run Number: ")

        # Show the dialog and get the user input
        subject_info = info_dialog.show()

        if not info_dialog.OK:
            core.quit()  # Exit if the user cancels

        # Extract the input fields and strip any whitespace
        participant_initials = subject_info[0].strip()
        subnum = subject_info[1].strip()
        run_num = subject_info[2].strip()

        # Validate inputs
        if not participant_initials:
            print("Error: Participant Initials cannot be empty.")
            continue

        # Validate and convert subject and run numbers
        try:
            subnum = int(subnum)  # Convert to integer
        except ValueError:
            print(f"Error: Subject Number '{subnum}' must be a valid number.")
            continue

        try:
            run_num = int(run_num)  # Convert to integer
        except ValueError:
            print(f"Error: Run Number '{run_num}' must be a valid number.")
            continue

        # If inputs are valid, return the information
        return {"Participant Initials": participant_initials, "Subject Number": subnum, "Run Number": run_num}
# Key catch function to quit the experiment
def check_quit_key():
    keys = event.getKeys()
    if 'escape' in keys:  # Catch the 'Escape' key as a quit trigger
        print("Experiment terminated by user.")
        core.quit()
        
def create_window():
    screen_number = 0  # Specify the screen if needed
    win = visual.Window(fullscr=full_screen, screen=screen_number, color=background_color,
                        colorSpace='rgb', units='height', waitBlanking=True)
    return win


# Function to show the instruction screen
def show_instruction(win, TR, TRs_per_trial):
    # Example TextStim usage
    instruction_text = visual.TextStim(win, text="Please move \n\n or attempt to move \n\n the body part instructed on the screen", 
                                    color=text_color, height=instruction_text_size, units='height')
    instruction_text.draw()
    win.flip()
    core.wait(TR * TRs_per_trial)

def show_waiting_for_scanner(win):
    waiting_text = visual.TextStim(win, text="Waiting for scanner", color=text_color, height=instruction_text_size, units='height')
    waiting_text.draw()
    win.flip()

# Function to show fixation cross for dummy scans or rest periods
def show_fixation(win, TR, TRs_duration, text="REST"):
    fixation_cross = visual.TextStim(win, text=text, color=text_color, height=fixation_text_size, units='height')
    for _ in range(TRs_duration):
        fixation_cross.draw()
        win.flip()
        core.wait(TR)

# Function to handle dummy scans before first rest
def handle_dummy_scans(win, TR, TRs_dummy_scans):
    if TRs_dummy_scans > 0:
        show_fixation(win, TR, TRs_dummy_scans, text="REST")  
#  function to calculate display time per countdown image
def calculate_image_display_time(trial_duration):
    return trial_duration / 12

def display_countdown(win, images, display_time, trial_text):

    for img in images:
        img.draw()          # Draw the countdown image
        trial_text.draw()    # Draw the trial text on top of the image
        win.flip()
        core.wait(display_time)  # Hold each image for calculated display time


def run_trial(win, condition, TR, TRs_per_trial, countdown_images, global_clock):
    # Set up the trial text (e.g., "MOVE LEFT HAND") that remains visible during the entire trial
    trial_text = visual.TextStim(win, text=f"MOVE {condition}", color=text_color, height=instruction_text_size, units='height')
    
    # Calculate trial duration and per-image display time for countdown
    trial_duration = TR * TRs_per_trial
    display_time = calculate_image_display_time(trial_duration)

    # Get the trial onset time from global_clock
    onset_time = global_clock.getTime()
    logging.debug(f"Trial {condition} started at {onset_time} seconds")

    # Display countdown with trial text overlay
    display_countdown(win, countdown_images, display_time, trial_text)

    # Log the end time based on global_clock
    end_time = global_clock.getTime()
    logging.debug(f"Trial {condition} ended at {end_time} seconds")

    return onset_time, end_time - onset_time  # Return onset time and duration

def show_rest_with_countdown(win, TR, TRs_duration, countdown_images):
    """
    Display a rest screen with a countdown timer.

    Parameters:
    win (psychopy.visual.Window): The Psychopy window for display.
    TR (float): Duration of each TR (Repetition Time) in seconds.
    TRs_duration (int): Number of TRs for the rest period.
    countdown_images (list): List of ImageStim objects representing countdown images.
    """
    # Set up rest text
    rest_text = visual.TextStim(win, text="REST", color=text_color, height=fixation_text_size, units='height')

    # Calculate rest duration and display time per countdown image
    rest_duration = TR * TRs_duration
    display_time = calculate_image_display_time(rest_duration)

    # Show countdown with rest text overlay
    display_countdown(win, countdown_images, display_time, rest_text)