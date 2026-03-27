#!/usr/bin/env python3
"""
BodyLocaliser -- fMRI motor-imagery localiser experiment.

Run via the platform launchers (mac_run_experiment.command / windows_run_experiment.bat)
or directly with:  python src/main.py   (from the project root).
Edit src/parameters.py to configure timing, conditions, and display settings.
"""

import csv
import logging
import os
import random
import shutil
import time
import warnings

from psychopy import core

from parameters import (
    BLOCKS,
    COND_NAMES,
    PORT_ADDRESS,
    SERIAL_PORT,
    TR,
    TRIGGER_INPUT_METHOD,
    TRIGGER_VALUE,
    TRs_dummy_scans,
    TRs_instruction,
    TRs_per_trial,
    TRs_rest,
)
from functions import (
    check_quit_key,
    create_window,
    handle_dummy_scans,
    load_countdown_images,
    resource_path,
    run_trial,
    show_instruction,
    show_rest_with_countdown,
    show_waiting_for_scanner,
    wait_for_trigger,
    get_subject_info,
)

warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trial schedule generation
# ---------------------------------------------------------------------------

def generate_trial_schedule():
    """Build the full list of trial and rest entries.

    Conditions are shuffled within each block so every condition appears
    exactly once per block. Rest periods are inserted between blocks and
    after the final block.

    Returns a list of dicts with keys:
        block, trial, condition, simulated_onset, duration
    """
    schedule = []
    t = 0.0
    trial_duration = TR * TRs_per_trial
    rest_duration = TR * TRs_rest

    for block in range(1, BLOCKS + 1):
        block_conditions = random.sample(COND_NAMES, len(COND_NAMES))

        for trial_num, condition in enumerate(block_conditions, start=1):
            schedule.append({
                "block": block,
                "trial": trial_num,
                "condition": condition,
                "simulated_onset": t,
                "duration": trial_duration,
            })
            t += trial_duration

        # Inter-block rest (also after the last block)
        schedule.append({
            "block": block,
            "trial": "rest" if block < BLOCKS else "final_rest",
            "condition": "REST",
            "simulated_onset": t,
            "duration": rest_duration,
        })
        t += rest_duration

    return schedule


# ---------------------------------------------------------------------------
# Data I/O helpers
# ---------------------------------------------------------------------------

def save_schedule_csv(schedule, path):
    """Write the pre-generated trial schedule to a CSV file."""
    fields = ["block", "trial", "condition", "simulated_onset", "duration"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(schedule)


def save_onset_1d_files(onset_dict, data_dir, subnum, run_num, datetag):
    """Write per-condition .1D onset files (AFNI format)."""
    for condition, onsets in onset_dict.items():
        if not onsets:
            continue
        path = os.path.join(
            data_dir,
            f"sub-{subnum}_run-{run_num}_{condition}_{datetag}.1D",
        )
        with open(path, "w") as fh:
            fh.write(" ".join(f"{o:.2f}" for o in onsets) + "\n")


def save_overall_log(log_entries, path):
    """Write the cumulative experiment log to CSV."""
    fields = ["block", "trial", "condition", "onset_time", "duration", "cumulative_onset"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(log_entries)


def save_presentation_order(schedule, path):
    """Write a human-readable presentation order file."""
    with open(path, "w") as fh:
        for entry in schedule:
            fh.write(
                f'Block: {entry["block"]}, '
                f'Trial: {entry["trial"]}, '
                f'Condition: {entry["condition"]}, '
                f'Simulated Onset: {entry["simulated_onset"]}, '
                f'Duration: {entry["duration"]}\n'
            )


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main():
    # ---- Subject info & output directory ----
    subject_info = get_subject_info()
    initials = subject_info["initials"]
    subnum = subject_info["subject_number"]
    run_num = subject_info["run_number"]

    random.seed(subnum + run_num)

    datetag = time.strftime("%Y_%m_%d_%H_%M")
    data_dir = resource_path(os.path.join("data", f"sub-{subnum}_{initials}"))
    os.makedirs(data_dir, exist_ok=True)

    # Save a snapshot of the parameters used for this run
    shutil.copy(
        resource_path(os.path.join("src", "parameters.py")),
        os.path.join(data_dir, f"parameters_{datetag}.py"),
    )

    # ---- Generate and persist trial schedule ----
    schedule = generate_trial_schedule()
    save_schedule_csv(
        schedule,
        os.path.join(data_dir, f"sub-{subnum}_run-{run_num}_trial_schedule_{datetag}.csv"),
    )

    # ---- Prepare onset logging ----
    onset_dict = {name: [] for name in list(COND_NAMES) + ["REST"]}
    overall_log = []

    # ---- PsychoPy window & stimuli ----
    win = create_window()
    countdown_images = load_countdown_images(win)

    try:
        # ---- Instructions & trigger ----
        show_instruction(win, TR, TRs_instruction)
        show_waiting_for_scanner(win)
        wait_for_trigger(
            input_method=TRIGGER_INPUT_METHOD,
            trigger_value=TRIGGER_VALUE,
            port_address=PORT_ADDRESS,
            serial_port=SERIAL_PORT,
        )
        check_quit_key()

        # ---- Dummy scans ----
        handle_dummy_scans(win, TR, TRs_dummy_scans)
        check_quit_key()

        # ---- Global clock starts now ----
        global_clock = core.Clock()

        # ---- Initial rest ----
        initial_rest_onset = global_clock.getTime()
        onset_dict["REST"].append(initial_rest_onset)
        show_rest_with_countdown(win, TR, TRs_rest, countdown_images)
        check_quit_key()

        overall_log.append({
            "block": 0,
            "trial": "initial_rest",
            "condition": "REST",
            "onset_time": initial_rest_onset,
            "duration": TR * TRs_rest,
            "cumulative_onset": initial_rest_onset + TR * TRs_rest,
        })

        # ---- Run trials from schedule ----
        for entry in schedule:
            check_quit_key()

            if entry["condition"] == "REST":
                rest_onset = global_clock.getTime()
                onset_dict["REST"].append(rest_onset)
                show_rest_with_countdown(
                    win, TR, int(entry["duration"] / TR), countdown_images
                )
                overall_log.append({
                    "block": entry["block"],
                    "trial": entry["trial"],
                    "condition": "REST",
                    "onset_time": rest_onset,
                    "duration": entry["duration"],
                    "cumulative_onset": rest_onset + entry["duration"],
                })
            else:
                onset_time, duration = run_trial(
                    win,
                    entry["condition"],
                    TR,
                    TRs_per_trial,
                    countdown_images,
                    global_clock,
                )
                onset_dict[entry["condition"]].append(onset_time)
                overall_log.append({
                    "block": entry["block"],
                    "trial": entry["trial"],
                    "condition": entry["condition"],
                    "onset_time": onset_time,
                    "duration": duration,
                    "cumulative_onset": onset_time + duration,
                })

    finally:
        # ---- Always save data, even on early exit ----
        save_onset_1d_files(onset_dict, data_dir, subnum, run_num, datetag)

        log_path = os.path.join(
            data_dir,
            f"BodyLoc_sub-{subnum}_{initials}_run{run_num}_{datetag}.csv",
        )
        save_overall_log(overall_log, log_path)

        save_presentation_order(
            schedule,
            os.path.join(
                data_dir,
                f"sub-{subnum}_run-{run_num}_presentation_order_{datetag}.txt",
            ),
        )

        win.close()
        logger.info("Output files saved to %s", data_dir)

    core.quit()


if __name__ == "__main__":
    main()
