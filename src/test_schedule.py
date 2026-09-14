"""Check the run orders and the trial schedule, without PsychoPy or a screen.

Run from the project root:  python3 src/test_schedule.py
"""
from collections import Counter

from parameters import (
    BLOCKS,
    COND_NAMES,
    TR,
    TRs_dummy_scans,
    TRs_final_rest,
    TRs_per_trial,
    TRs_rest,
)
from run_orders import RUN_ORDERS
from schedule import (MID_REST, check_parameters, generate_trial_schedule, measurements,
                      run_order_blocks)

N = len(COND_NAMES)
TRIAL, REST, FINAL = TR * TRs_per_trial, TR * TRs_rest, TR * TRs_final_rest
MID_AFTER = min(MID_REST, N)          # trials before the rest inside a block
HAS_MID = 0 < MID_AFTER < N
BLOCK_LAYOUT = "M" * MID_AFTER + "R" * HAS_MID + "M" * (N - MID_AFTER) + "R"

check_parameters()

for blocks, orders in RUN_ORDERS.items():
    # The 7 preset orders: every movement fills every place of every block exactly once.
    assert sorted(orders) == list(range(1, N + 1)), blocks
    assert all(sorted(b) == sorted(COND_NAMES) for o in orders.values() for b in o), blocks
    places = Counter((b, place, c) for o in orders.values()
                     for b, block in enumerate(o) for place, c in enumerate(block))
    assert len(places) == blocks * N * N and set(places.values()) == {1}, blocks

    for run_order in [*orders, "random"]:
        run = run_order_blocks(run_order, subnum=1, blocks=blocks)
        schedule = generate_trial_schedule(run)
        assert len(run) == blocks, (blocks, run_order)
        if run_order != "random":
            assert run == orders[run_order], (blocks, run_order)
        assert [e["condition"] for e in schedule if e["condition"] != "REST"] == sum(run, []), run_order
        assert "".join("R" if e["condition"] == "REST" else "M"
                       for e in schedule) == "R" + BLOCK_LAYOUT * blocks, (blocks, run_order)
        assert all(e["simulated_onset"] % TR == 0 for e in schedule), (blocks, run_order)
        assert schedule[-1]["duration"] == FINAL, (blocks, run_order)
        end = schedule[-1]["simulated_onset"] + schedule[-1]["duration"]
        assert end == REST + blocks * (N * TRIAL + REST * HAS_MID) + (blocks - 1) * REST + FINAL
        assert measurements(schedule) == TRs_dummy_scans + round(end / TR), (blocks, run_order)

    # Balanced random is preset order 1 with the movements relabelled.
    relabel = {}
    for a, b in zip(sum(orders[1], []), sum(run_order_blocks("random", 7, blocks=blocks), [])):
        assert relabel.setdefault(a, b) == b, blocks
    assert sorted(relabel.values()) == sorted(COND_NAMES), blocks

# Balanced random: fixed for a subject, different between subjects.
assert run_order_blocks("random", 7) == run_order_blocks("random", 7)
assert run_order_blocks("random", 7) != run_order_blocks("random", 8)

schedule = generate_trial_schedule(run_order_blocks(1, subnum=1))
scan = schedule[-1]["simulated_onset"] + schedule[-1]["duration"]
print(f"OK: {len(RUN_ORDERS)} block counts x {N} preset orders, plus balanced random. "
      f"parameters.py: {BLOCKS} blocks, {scan:.0f} s, {measurements(schedule)} measurements")
