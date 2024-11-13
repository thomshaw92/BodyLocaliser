from psychopy import core, event
import shutil
from functions import *
from parameters import *
import random
import time
import os
import csv
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Gather subject info
subject_info = get_subject_info()
participant_initials = subject_info["Participant Initials"]
subnum = int(subject_info["Subject Number"])
run_num = int(subject_info["Run Number"])

# Set random seed for reproducibility
random.seed(subnum + run_num)

# Generate datetime and data directory for saving files
datetag = time.strftime("%Y_%m_%d_%H_%M")
data_dir = f'Data/sub-{subnum}_{participant_initials}/'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Save parameters.py into the data directory
shutil.copy("parameters.py", os.path.join(data_dir, f"parameters_{datetag}.py"))

def check_quit_key():
    keys = event.getKeys()
    if 'escape' in keys:
        print("Experiment terminated by user.")
        core.quit()  # Gracefully exit PsychoPy

# Define trial structure and generate a full schedule in memory
def generate_trial_schedule(blocks, trials_per_block, TR, cond_names):
    trial_schedule = []
    simulated_time = 0.0

    for block in range(1, blocks + 1):
        # Shuffle conditions for each block, ensuring each condition appears once per block
        block_conditions = random.sample(cond_names, len(cond_names))

        for trial_num, condition in enumerate(block_conditions, start=1):
            trial_schedule.append({
                "block": block,
                "trial": trial_num,
                "condition": condition,
                "simulated_onset": simulated_time,
                "duration": TR * TRs_per_trial
            })
            simulated_time += TR * TRs_per_trial

        # Add rest period after each block (excluding the last block)
        if block < blocks:
            trial_schedule.append({
                "block": block,
                "trial": "rest",
                "condition": "REST",
                "simulated_onset": simulated_time,
                "duration": TR * TRs_rest
            })
            simulated_time += TR * TRs_rest

    # Final rest period after the last block
    trial_schedule.append({
        "block": blocks,
        "trial": "final_rest",
        "condition": "REST",
        "simulated_onset": simulated_time,
        "duration": TR * TRs_rest
    })

    return trial_schedule

# Generate and save the trial schedule in memory
trial_schedule = generate_trial_schedule(blocks, trials_per_block, TR, cond_names)

# Save the trial schedule to a CSV for logging purposes
schedule_filename = os.path.join(data_dir, f"sub-{subnum}_run-{run_num}_trial_schedule_{datetag}.csv")
with open(schedule_filename, 'w', newline='') as csvfile:
    fieldnames = ["block", "trial", "condition", "simulated_onset", "duration"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in trial_schedule:
        writer.writerow(entry)

# Initialize onset logging structures for each condition
onset_dict = {name: [] for name in cond_names + ["REST"]}
overall_log = []

# Create PsychoPy window
win = create_window()
countdown_images = [
    visual.ImageStim(win, image=f'images/{i}.png', size=countdown_image_size, pos=countdown_image_position) for i in range(1, 13)
]

# Show instructions and wait for scanner trigger
show_instruction(win, TR, TRs_instruction)
show_waiting_for_scanner(win)
wait_for_trigger(input_method=trigger_input_method, trigger_value=trigger_value)
check_quit_key()

# Handle dummy scans with fixation cross
handle_dummy_scans(win, TR, TRs_dummy_scans)
check_quit_key()

# Initialize the global clock after dummy scans and initial rest
global_clock = core.Clock()

# Capture onset for the initial rest period
initial_rest_onset = global_clock.getTime()
onset_dict["REST"].append(initial_rest_onset)
show_rest_with_countdown(win, TR, TRs_rest, countdown_images)
check_quit_key()

# Log the initial rest period in the overall log
overall_log.append({
    "block": 0,
    "trial": "initial_rest",
    "condition": "REST",
    "onset_time": initial_rest_onset,
    "duration": TR * TRs_rest,
    "cumulative_onset": initial_rest_onset + (TR * TRs_rest)
})

# Execute the experiment based on the in-memory trial schedule
for entry in trial_schedule:
    check_quit_key()

    if entry["condition"] == "REST":
        # Display rest with countdown timer and log the rest onset time
        rest_onset = global_clock.getTime()
        onset_dict["REST"].append(rest_onset)
        show_rest_with_countdown(win, TR, int(entry["duration"] / TR), countdown_images)
        
        # Log rest period in the overall log
        overall_log.append({
            "block": entry["block"],
            "trial": entry["trial"],
            "condition": "REST",
            "onset_time": rest_onset,
            "duration": entry["duration"],
            "cumulative_onset": rest_onset + entry["duration"]
        })
    else:
        # Display the trial for the specified condition
        condition_name = entry["condition"]
        onset_time, duration = run_trial(win, condition_name, TR, TRs_per_trial, countdown_images, global_clock)

        # Record onset time for each condition
        onset_dict[condition_name].append(onset_time)
        
        # Append detailed trial information to overall log
        overall_log.append({
            "block": entry["block"],
            "trial": entry["trial"],
            "condition": condition_name,
            "onset_time": onset_time,
            "duration": duration,
            "cumulative_onset": onset_time + duration
        })

# Save the onset times for each condition and REST as separate .1D files
for condition, onsets in onset_dict.items():
    if onsets:  # Only save if there are onsets for this condition
        onset_filename = f'{data_dir}/sub-{subnum}_run-{run_num}_{condition}_{datetag}.1D'
        with open(onset_filename, 'w') as onset_file:
            onset_file.write(' '.join([f'{onset:.2f}' for onset in onsets]) + '\n')

# Save the overall log to a CSV file
filename = f'BodyLoc_sub-{subnum}_{participant_initials}_run{run_num}_{datetag}.csv'
with open(os.path.join(data_dir, filename), 'w', newline='') as csvfile:
    fieldnames = ["block", "trial", "condition", "onset_time", "duration", "cumulative_onset"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in overall_log:
        writer.writerow(entry)

# Save the condition presentation order
order_filename = os.path.join(data_dir, f"sub-{subnum}_run-{run_num}_presentation_order_{datetag}.txt")
with open(order_filename, 'w') as order_file:
    for entry in trial_schedule:
        order_file.write(f'Block: {entry["block"]}, Trial: {entry["trial"]}, Condition: {entry["condition"]}, '
                        f'Simulated Onset: {entry["simulated_onset"]}, Duration: {entry["duration"]}\n')

# Close PsychoPy window and end experiment
win.close()
core.quit()
print(f"Output files saved to {data_dir}")