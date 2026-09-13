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
)
from functions import (
    TriggerLog,
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
from schedule import check_parameters, generate_trial_schedule, measurements, run_order_blocks

warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data I/O helpers
# ---------------------------------------------------------------------------

def save_schedule_csv(schedule, path):
    """Write the pre-generated trial schedule to a CSV file."""
    fields = ["block", "trial", "condition", "simulated_onset", "duration", "run_order"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(schedule)


def save_onset_1d_files(onset_dict, data_dir, prefix, datetag):
    """Write per-condition .1D onset files (AFNI format)."""
    for condition, onsets in onset_dict.items():
        if not onsets:
            continue
        path = os.path.join(data_dir, f"{prefix}_{condition}_{datetag}.1D")
        with open(path, "w") as fh:
            fh.write(" ".join(f"{o:.2f}" for o in onsets) + "\n")


def save_overall_log(log_entries, path):
    """Write the cumulative experiment log to CSV."""
    fields = ["block", "trial", "condition", "onset_time", "duration", "cumulative_onset", "run_order"]
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(log_entries)


def save_trigger_csv(times, path, TR):
    """Write when every scanner trigger arrived, timed from the first one.

    The scanner pulses at the start of each TR, so `interval` should sit at TR and
    `drift` shows how far the volume count has slipped from the ideal grid.
    """
    first = times[0] if times else 0.0
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["volume", "time", "interval", "drift"])
        for i, t in enumerate(times):
            since = t - first
            writer.writerow([i, f"{since:.4f}",
                             "" if i == 0 else f"{t - times[i - 1]:.4f}",
                             f"{since - i * TR:+.4f}"])


def save_presentation_order(schedule, path, header=""):
    """Write a human-readable presentation order file."""
    with open(path, "w") as fh:
        if header:
            fh.write(header + "\n")
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
    check_parameters()

    # ---- Subject info & output directory ----
    subject_info = get_subject_info()
    initials = subject_info["initials"]
    subnum = subject_info["subject_number"]
    run_num = subject_info["run_number"]
    run_order = subject_info["run_order"]  # a preset run order number, or "random"

    blocks = run_order_blocks(run_order, subnum)

    datetag = time.strftime("%Y_%m_%d_%H_%M")
    data_dir = resource_path(os.path.join("data", f"sub-{subnum}_{initials}"))
    os.makedirs(data_dir, exist_ok=True)
    prefix = f"sub-{subnum}_run-{run_num}_order-{run_order}"

    # Save a snapshot of the parameters used for this run
    shutil.copy(
        resource_path(os.path.join("src", "parameters.py")),
        os.path.join(data_dir, f"parameters_order-{run_order}_{datetag}.py"),
    )

    # ---- Generate and persist trial schedule ----
    schedule = generate_trial_schedule(blocks)
    for entry in schedule:
        entry["run_order"] = run_order
    save_schedule_csv(
        schedule,
        os.path.join(data_dir, f"{prefix}_trial_schedule_{datetag}.csv"),
    )

    volumes = measurements(schedule)
    order_text = "Balanced random order" if run_order == "random" else f"Run order {run_order}"
    detail = f"{order_text}, {BLOCKS} blocks, {volumes} measurements"
    logger.info("%s: the scan needs %d measurements", order_text, volumes)

    # ---- Prepare onset logging ----
    onset_dict = {name: [] for name in list(COND_NAMES) + ["REST"]}
    overall_log = []

    # ---- PsychoPy window & stimuli ----
    win = create_window()
    countdown_images = load_countdown_images(win)

    # A screen too slow to reach the next image on time shortens epochs rather than
    # adding volumes, which is silent, so report what this screen does.
    refresh = win.getActualFrameRate()
    frames_per_image = refresh * TR * TRs_per_trial / len(countdown_images) if refresh else None
    if refresh:
        detail += f"\n{refresh:.0f} Hz screen, {frames_per_image:.0f} frames per countdown image"
        logger.info("Screen: %.1f Hz, %.1f frames per countdown image", refresh, frames_per_image)
    else:
        detail += "\nScreen refresh could not be measured"
        logger.warning("Could not measure the screen refresh rate")
    if frames_per_image is not None and frames_per_image < 2:
        detail += "\nWARNING: too few frames per image, epochs will be shortened"
        logger.warning("Only %.1f frames per countdown image; this screen cannot keep up",
                       frames_per_image)

    triggers, run_start = None, None
    try:
        # ---- Instructions & trigger ----
        show_instruction(win, TR, TRs_instruction)
        show_waiting_for_scanner(win, detail)

        # Every trigger is recorded, not just the first: the scanner pulses at the start
        # of each TR, so the times are a check on its timing against the schedule.
        triggers = TriggerLog(core.Clock(), TRIGGER_INPUT_METHOD, TRIGGER_VALUE,
                              PORT_ADDRESS, SERIAL_PORT)
        wait_for_trigger(triggers)
        check_quit_key()

        # ---- Dummy scans ----
        handle_dummy_scans(win, TR, TRs_dummy_scans, triggers)
        check_quit_key()

        # ---- Global clock starts now ----
        global_clock = core.Clock()
        # The run log is timed from here, the trigger file from the first trigger. They
        # are the same instant only when there are no dummy scans, so record the gap
        # rather than leave anyone aligning the two files to assume it.
        run_start = triggers.clock.getTime() - triggers.times[0]
        logger.info("Run clock starts %+.4f s after the first trigger", run_start)

        # ---- Run rests and trials from schedule ----
        # Every entry ends at its scheduled time on the global clock, so a flip that
        # lands late costs that entry alone instead of delaying the whole run.
        for entry in schedule:
            check_quit_key()

            end_time = entry["simulated_onset"] + entry["duration"]
            if entry["condition"] == "REST":
                onset_time = show_rest_with_countdown(
                    win, countdown_images, global_clock, end_time, triggers
                )
            else:
                onset_time = run_trial(
                    win, entry["condition"], countdown_images, global_clock, end_time,
                    triggers
                )
            duration = global_clock.getTime() - onset_time
            onset_dict[entry["condition"]].append(onset_time)
            overall_log.append({
                "block": entry["block"],
                "trial": entry["trial"],
                "condition": entry["condition"],
                "onset_time": onset_time,
                "duration": duration,
                "cumulative_onset": onset_time + duration,
                "run_order": run_order,
            })

        planned = schedule[-1]["simulated_onset"] + schedule[-1]["duration"]
        logger.info("Run ended %+.3f s from the scheduled %.1f s",
                    global_clock.getTime() - planned, planned)
        logger.info("Scanner triggers recorded: %d, expected %d", len(triggers.times), volumes)
        if len(triggers.times) != volumes:
            logger.warning("Trigger count does not match the %d measurements expected",
                           volumes)

    finally:
        # ---- Always save data, even on early exit ----
        save_onset_1d_files(onset_dict, data_dir, prefix, datetag)

        log_path = os.path.join(
            data_dir,
            f"BodyLoc_sub-{subnum}_{initials}_run{run_num}_order-{run_order}_{datetag}.csv",
        )
        save_overall_log(overall_log, log_path)

        save_presentation_order(
            schedule,
            os.path.join(data_dir, f"{prefix}_presentation_order_{datetag}.txt"),
            header=("Screen: " + (f"{refresh:.1f} Hz" if refresh else "refresh not measured")
                    + ("" if run_start is None else
                       f"; run clock starts {run_start:+.4f} s after the first trigger")),
        )

        if triggers is not None:
            save_trigger_csv(
                triggers.times,
                os.path.join(data_dir, f"{prefix}_triggers_{datetag}.csv"),
                TR,
            )
            triggers.close()

        win.close()
        logger.info("Output files saved to %s", data_dir)

    core.quit()


if __name__ == "__main__":
    main()
