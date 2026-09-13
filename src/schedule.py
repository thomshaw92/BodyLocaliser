"""What happens when in a BodyLocaliser run: run orders and the trial schedule.

No PsychoPy here, so the schedule can be checked and printed without a screen
(src/test_schedule.py, src/design.py).
"""
import random
import re

from parameters import (
    BLOCKS,
    COND_NAMES,
    MID_BLOCK_REST_AFTER,
    NUM_COUNTDOWN_IMAGES,
    PORT_ADDRESS,
    SERIAL_PORT,
    TR,
    TRIGGER_INPUT_METHOD,
    TRs_dummy_scans,
    TRs_final_rest,
    TRs_instruction,
    TRs_per_trial,
    TRs_rest,
)
from run_orders import RUN_ORDERS


def centred_rest(n):
    """Where the rest inside a block falls when MID_BLOCK_REST_AFTER is None.

    The middle of the block, which needs at least two movements on each side; with
    fewer than four movements there is no room and the block gets no interior rest.
    """
    return -(-n // 2) if n >= 4 else 0


# What parameters.py asked for, with None resolved. Everything reads this, not the raw value.
MID_REST = (centred_rest(len(COND_NAMES)) if MID_BLOCK_REST_AFTER is None
            else MID_BLOCK_REST_AFTER)


def run_order_blocks(run_order, subnum, blocks=BLOCKS):
    """Return the blocks (lists of conditions) for *run_order*.

    1 to the number of movements gives that preset OpenRecon run order, for *blocks* blocks.
    "random" gives preset order 1 with the conditions relabelled by a shuffle
    seeded on the subject number: relabelling keeps every balance rule of the
    preset orders, and a subject gets the same order at every session.
    """
    orders = RUN_ORDERS[blocks]
    if run_order == "random":
        rng = random.Random(f"sub-{subnum}")
        relabel = dict(zip(COND_NAMES, rng.sample(COND_NAMES, len(COND_NAMES))))
        return [[relabel[c] for c in block] for block in orders[1]]
    return orders[run_order]


def generate_trial_schedule(blocks):
    """Build the full list of rest and trial entries, starting with the initial rest.

    Each block presents its conditions in the given order, with a rest after
    trial MID_REST and after the block (TRs_final_rest after the
    last block).

    Returns a list of dicts with keys:
        block, trial, condition, simulated_onset, duration
    """
    rest = TR * TRs_rest
    schedule = [{"block": 0, "trial": "initial_rest", "condition": "REST", "duration": rest}]

    for block, conditions in enumerate(blocks, start=1):
        for trial_num, condition in enumerate(conditions, start=1):
            schedule.append({
                "block": block,
                "trial": trial_num,
                "condition": condition,
                "duration": TR * TRs_per_trial,
            })
            if trial_num == MID_REST:
                schedule.append({"block": block, "trial": "mid_rest", "condition": "REST", "duration": rest})

        last = block == len(blocks)
        schedule.append({
            "block": block,
            "trial": "final_rest" if last else "rest",
            "condition": "REST",
            "duration": TR * TRs_final_rest if last else rest,
        })

    t = 0.0
    for entry in schedule:
        entry["simulated_onset"] = t
        t += entry["duration"]
    return schedule


def measurements(schedule):
    """Volumes the scanner must collect: the dummy scans plus the whole schedule."""
    return TRs_dummy_scans + round(sum(e["duration"] for e in schedule) / TR)


def check_parameters():
    """Raise SystemExit if parameters.py cannot give a valid run.

    Everything checked here either crashes after the scanner has started, or
    quietly changes the timing the OpenRecon container assumes.
    """
    n = len(COND_NAMES)
    problems = []

    if len(set(COND_NAMES)) != n or "REST" in COND_NAMES:
        problems.append("COND_NAMES must be unique and must not contain REST")
    unsafe = [c for c in COND_NAMES if not re.fullmatch(r"[A-Za-z0-9 _-]+", str(c))]
    if unsafe:
        problems.append(f"COND_NAMES goes into the output file names, so use only letters, "
                        f"digits, spaces, - and _: {', '.join(map(repr, unsafe))}")
    if BLOCKS not in RUN_ORDERS:
        problems.append(f"no preset run orders for {BLOCKS!r} blocks; run_orders.py holds "
                        f"{', '.join(str(b) for b in sorted(RUN_ORDERS))}. "
                        f"Run python3 tools/make_run_orders.py to build more")
    else:
        preset = sorted(RUN_ORDERS[BLOCKS][1][0])
        rebuild = ("Run python3 tools/make_run_orders.py to rebuild it, "
                   "and give the OpenRecon container the new file")
        if len(preset) != n:
            problems.append(f"no preset run orders for these {n} movements; run_orders.py was "
                            f"built for {len(preset)}. {rebuild}")
        elif preset != sorted(COND_NAMES):
            problems.append(f"COND_NAMES does not match the movements in run_orders.py "
                            f"({', '.join(preset)}). {rebuild}")
    if not isinstance(TR, (int, float)) or TR <= 0:
        problems.append(f"TR must be a positive number of seconds, not {TR!r}")
    for name, value, least in [("TRs_per_trial", TRs_per_trial, 1), ("TRs_rest", TRs_rest, 1),
                               ("TRs_final_rest", TRs_final_rest, 1),
                               ("TRs_dummy_scans", TRs_dummy_scans, 0),
                               ("TRs_instruction", TRs_instruction, 0)]:
        if not isinstance(value, int) or value < least:
            problems.append(f"{name} must be a whole number of TRs, {least} or more, not {value!r}")
    if MID_BLOCK_REST_AFTER is None:
        pass                                 # centred on the movements, so always in range
    elif not isinstance(MID_BLOCK_REST_AFTER, int) or not 0 <= MID_BLOCK_REST_AFTER < n:
        problems.append(f"MID_BLOCK_REST_AFTER must be None (centred), 0 (no rest inside a "
                        f"block) or a whole number up to {n - 1}, not {MID_BLOCK_REST_AFTER!r}")
    elif MID_BLOCK_REST_AFTER and not 2 <= MID_BLOCK_REST_AFTER <= n - 2:
        # One movement between two rests is scanned in a different context from the rest of
        # its block, and the position does not follow COND_NAMES when it changes.
        if n >= 4:
            problems.append(f"MID_BLOCK_REST_AFTER of {MID_BLOCK_REST_AFTER} leaves fewer than two "
                            f"movements on one side of the rest; with {n} movements use 2 to "
                            f"{n - 2}, about half being usual, or 0 for no rest inside a block")
        else:
            problems.append(f"{n} movements leave no room for a rest inside a block; set "
                            f"MID_BLOCK_REST_AFTER to 0")
    if not isinstance(NUM_COUNTDOWN_IMAGES, int) or NUM_COUNTDOWN_IMAGES < 1:
        problems.append(f"NUM_COUNTDOWN_IMAGES must be a whole number, 1 or more, not "
                        f"{NUM_COUNTDOWN_IMAGES!r}")
    if TRIGGER_INPUT_METHOD not in ("key", "parallel", "serial"):
        problems.append(f"TRIGGER_INPUT_METHOD must be key, parallel or serial, "
                        f"not {TRIGGER_INPUT_METHOD!r}")
    elif TRIGGER_INPUT_METHOD == "parallel" and PORT_ADDRESS is None:
        problems.append("TRIGGER_INPUT_METHOD is parallel, so PORT_ADDRESS must be set")
    elif TRIGGER_INPUT_METHOD == "serial" and SERIAL_PORT is None:
        problems.append("TRIGGER_INPUT_METHOD is serial, so SERIAL_PORT must be set")

    if problems:
        raise SystemExit("src/parameters.py:\n  " + "\n  ".join(problems))
