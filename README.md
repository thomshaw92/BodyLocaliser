# BodyLocaliser

A PsychoPy-based fMRI motor-imagery localiser. Participants are cued to move (or attempt to move) seven body parts while BOLD data is acquired. The task produces AFNI-compatible `.1D` onset files and CSV logs ready for first-level analysis.

## Conditions

Left Elbow, Right Elbow, Left Hand, Right Hand, Left Foot, Right Foot, Tongue.

Each condition appears once per block. After the participant details, the operator picks the run order:

- **OpenRecon run order 1 to 7**: a preset order from `src/run_orders.py`. The OpenRecon container holds the same orders, so set the same number on the scanner protocol card.
- **Balanced random**: run order 1 with the body parts relabelled by a shuffle seeded on the subject number, so each subject gets their own order, the same at every session, with the same balance as the preset orders. The container cannot know this order, so it is not for OpenRecon runs.

## Recommended design

4 blocks of 9 s trials, with 9 s rest before the first block, after the 4th trial of each block and between blocks, and 15 s after the last. That is 339 s, or 226 measurements at TR 1.5 s. The "Waiting for scanner" screen shows the run order, the number of blocks and the number of measurements, so they can be checked against the scanner protocol card.

## Quick start

The easiest way to run the experiment is with the platform launchers. They handle finding (or installing) a compatible Python, creating a virtual environment, and installing PsychoPy automatically.

**Mac:** Double-click `mac_run_experiment.command`. If macOS blocks it, right-click and choose Open.

**Windows:** Double-click `windows_run_experiment.bat`.

On first launch the script will create a `.venv` folder and install dependencies (this takes a few minutes). Subsequent launches skip straight to the experiment.

If you prefer to manage the environment yourself:

```bash
pip install -r requirements.txt
python src/main.py
```

A dialog will ask for participant initials, subject number, and run number, then a second dialog for the run order (see Conditions); it will not continue until one is chosen. Press `5` (or whatever `TRIGGER_VALUE` is set to) to start after the scanner begins. Press `Escape` at any time to abort -- partial data is still saved.

## Configuration

All tuneable settings live in `src/parameters.py`:

| Parameter | Default | Description |
|---|---|---|
| `TR` | 1.5 | Repetition time (seconds) |
| `TRs_per_trial` | 6 | Trial duration in TRs |
| `TRs_rest` | 6 | Rest duration in TRs |
| `TRs_final_rest` | 10 | Rest after the last block in TRs |
| `TRs_dummy_scans` | 0 | Dummy scans before first trial |
| `BLOCKS` | 4 | Blocks per run: 1 to 8, with 4 recommended (see Advanced use) |
| `MID_BLOCK_REST_AFTER` | 4 | A rest follows this trial in every block |
| `COND_NAMES` | 7 body parts | Conditions (one trial each per block) |
| `TRIGGER_INPUT_METHOD` | `'key'` | `'key'`, `'parallel'`, or `'serial'` |
| `TRIGGER_VALUE` | `'5'` | Key or byte the scanner sends |
| `FULL_SCREEN` | `True` | Set `False` for windowed testing |

## Advanced use

**A different number of blocks.** Set `BLOCKS` to anything from 1 to 8; `src/run_orders.py` holds 7 preset orders for each. The scan lasts 81 × blocks + 15 s with the default timings, and the run order dialog is unchanged. Fewer blocks means less precision, so 4 is the recommendation. Three block counts cannot meet every balance rule, and `src/run_orders.py` says so at the top: with 1 block the pairs of consecutive movements cannot be balanced, with 2 blocks a movement cannot be both early and late, and with 8 blocks a pair of movements may occur twice in a run.

**Print the design.** `python3 src/design.py` prints the settings, the scan length, the number of measurements and every movement onset, for each preset run order. Add a run order (`python3 src/design.py 3`) to print just that one. This is the spec sheet for the scanner and for the OpenRecon container, which has to match the timings printed at the top.

**Rebuild the run orders.** Only needed if the movements or the rules change: `python3 tools/make_run_orders.py` rewrites `src/run_orders.py`. It needs numpy and scipy, which the PsychoPy `.venv` already has, and takes a few minutes. Its output is deterministic, and the OpenRecon container must be given the same file.

**Check it.** `python3 src/test_schedule.py` checks the run orders and the schedule for every block count. Neither it nor `design.py` needs PsychoPy.

## Output

Data is saved to `data/sub-{N}_{initials}/`. See `data/README.md` for file format details.

## Building a standalone executable

```bash
pip install pyinstaller
pyinstaller build/main.spec
```

The bundle lands in `dist/BodyLocaliser/`. Copy the entire folder to the scanner PC.

## Project structure

```
BodyLocaliser/
├── mac_run_experiment.command   Mac launcher (double-click to run)
├── windows_run_experiment.bat   Windows launcher (double-click to run)
├── README.md                    This file
├── requirements.txt             Python dependencies
├── LICENSE                      BSD 3-Clause
├── src/                         Source code
│   ├── main.py                  Experiment entry point and flow control
│   ├── functions.py             Display, trigger, and I/O helpers
│   ├── parameters.py            All configurable settings
│   ├── schedule.py              Run orders and trial schedule (no PsychoPy)
│   ├── run_orders.py            Preset run orders per block count (generated; do not edit)
│   ├── design.py                Prints the design for the current settings
│   └── test_schedule.py         Checks the run orders and the schedule
├── tools/
│   └── make_run_orders.py       Rebuilds src/run_orders.py (needs numpy and scipy)
├── assets/                      Non-code resources
│   ├── images/                  Countdown timer images (1--12)
│   └── *.mp4                    Participant instruction video
├── data/                        Output (created at runtime, gitignored)
└── build/                       PyInstaller build configuration
```

## License

BSD 3-Clause. See `LICENSE`.
