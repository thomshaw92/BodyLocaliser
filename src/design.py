"""Print the design for the settings in src/parameters.py: the spec sheet for a run.

Run from the project root:
    python3 src/design.py                 every preset run order
    python3 src/design.py 3               just run order 3
    python3 src/design.py random 12       the balanced random order for subject 12

Needs no PsychoPy. The OpenRecon container must match the settings printed at the top.
"""
import sys

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
from schedule import generate_trial_schedule, measurements, run_order_blocks


def show(run_order, subnum):
    blocks = run_order_blocks(run_order, subnum)
    schedule = generate_trial_schedule(blocks)
    label = f"balanced random, subject {subnum}" if run_order == "random" else f"run order {run_order}"
    print(f"\n{label}")
    for number, block in enumerate(blocks, start=1):
        print(f"  block {number}: " + ", ".join(block))
    print("  onsets, seconds from the first trigger (volume number in brackets):")
    for name in list(COND_NAMES) + ["REST"]:
        onsets = [e["simulated_onset"] for e in schedule if e["condition"] == name]
        print(f"    {name:12s} " + " ".join(f"{o:6.1f} ({round(o / TR) + TRs_dummy_scans:3d})"
                                            for o in onsets))


def main(argv):
    run_order = argv[1] if len(argv) > 1 else None
    if run_order not in (None, "random"):
        run_order = int(run_order)
    subnum = int(argv[2]) if len(argv) > 2 else 1

    orders = [run_order] if run_order is not None else list(RUN_ORDERS[BLOCKS])
    schedule = generate_trial_schedule(run_order_blocks(orders[0], subnum))
    scan = sum(e["duration"] for e in schedule)
    print("BodyLocaliser design, from src/parameters.py")
    print(f"  blocks             {BLOCKS}  (run_orders.py holds {min(RUN_ORDERS)} to {max(RUN_ORDERS)})")
    print(f"  movements          {len(COND_NAMES)}, {TRs_per_trial} TRs each")
    print(f"  rest               {TRs_rest} TRs, after trial {MID_BLOCK_REST_AFTER} of each block "
          f"and after each block")
    print(f"  final rest         {TRs_final_rest} TRs")
    print(f"  dummy scans        {TRs_dummy_scans} TRs")
    print(f"  TR                 {TR} s")
    print(f"  scan               {scan:.0f} s, {measurements(schedule)} measurements")
    print(f"  preset run orders  {min(RUN_ORDERS[BLOCKS])} to {max(RUN_ORDERS[BLOCKS])}, "
          f"plus balanced random")

    for k in orders:
        show(k, subnum)


if __name__ == "__main__":
    main(sys.argv)
