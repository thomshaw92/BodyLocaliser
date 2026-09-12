# src/

Experiment source code.

| File | Purpose |
|---|---|
| `main.py` | Entry point -- experiment flow, trial scheduling, data output |
| `functions.py` | Display, trigger, and I/O helper functions |
| `parameters.py` | All configurable settings (timing, conditions, display, trigger) |
| `schedule.py` | Run orders and the trial schedule; no PsychoPy, so it can be checked and printed without a screen |
| `run_orders.py` | The 7 preset OpenRecon run orders for each block count, written by `tools/make_run_orders.py`; do not edit by hand |
| `design.py` | Prints the design for the current settings: `python3 src/design.py` |
| `test_schedule.py` | Checks the run orders and the schedule without PsychoPy: `python3 src/test_schedule.py` |

`parameters.py` is the only file most users need to edit. See the top-level README for a summary of what each parameter does.
