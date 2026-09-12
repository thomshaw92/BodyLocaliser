"""What happens when in a BodyLocaliser run: run orders and the trial schedule.

No PsychoPy here, so the schedule can be checked and printed without a screen
(src/test_schedule.py, src/design.py).
"""
import random

from parameters import (
    BLOCKS,
    COND_NAMES,
    MID_BLOCK_REST_AFTER,
    TR,
    TRs_dummy_scans,
    TRs_final_rest,
    TRs_per_trial,
    TRs_rest,
)
from run_orders import RUN_ORDERS


def run_order_blocks(run_order, subnum, blocks=BLOCKS):
    """Return the blocks (lists of conditions) for *run_order*.

    1-7 gives preset OpenRecon run order *run_order* for *blocks* blocks.
    "random" gives preset order 1 with the conditions relabelled by a shuffle
    seeded on the subject number: relabelling keeps every balance rule of the
    preset orders, and a subject gets the same order at every session.
    """
    if blocks not in RUN_ORDERS:
        raise ValueError(
            f"BLOCKS is {blocks} in parameters.py, but run_orders.py has "
            f"{min(RUN_ORDERS)} to {max(RUN_ORDERS)} blocks."
        )
    orders = RUN_ORDERS[blocks]
    if run_order == "random":
        rng = random.Random(f"sub-{subnum}")
        relabel = dict(zip(COND_NAMES, rng.sample(COND_NAMES, len(COND_NAMES))))
        return [[relabel[c] for c in block] for block in orders[1]]
    return orders[run_order]


def generate_trial_schedule(blocks):
    """Build the full list of rest and trial entries, starting with the initial rest.

    Each block presents its conditions in the given order, with a rest after
    trial MID_BLOCK_REST_AFTER and after the block (TRs_final_rest after the
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
            if trial_num == MID_BLOCK_REST_AFTER:
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
