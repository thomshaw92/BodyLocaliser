# BodyLocaliser

A PsychoPy-based fMRI motor-imagery localiser. Participants are cued to move (or attempt to move) seven body parts -- or whatever regions `COND_NAMES` lists -- while BOLD data is acquired. The task produces AFNI-compatible `.1D` onset files and CSV logs ready for first-level analysis.

## Conditions

Left Elbow, Right Elbow, Left Hand, Right Hand, Left Foot, Right Foot, Tongue.

Each condition appears once per block. After the participant details, the operator picks the run order:

- **OpenRecon run order 1 to N**: a preset order from `src/run_orders.py`, one per movement, so 1 to 7 with the default body parts (see Advanced use). The OpenRecon container holds the same orders, so set the same number on the scanner protocol card.
- **Balanced random**: run order 1 with the body parts relabelled by a shuffle seeded on the subject number, so each subject gets their own order, the same at every session, with the same balance as the preset orders. The container cannot know this order, so it is not for OpenRecon runs.

## Recommended design

4 blocks of 9 s trials, with 9 s rest before the first block, after the 4th trial of each block and between blocks, and 15 s after the last. That is 339 s, or 226 measurements at TR 1.5 s. The "Waiting for scanner" screen shows the run order, the number of blocks and the number of measurements, so they can be checked against the scanner protocol card. It also shows the screen's measured refresh rate and how many frames each countdown image gets. The measurement count is the same on every screen -- epochs are held to absolute times, so a slower screen does not add volumes -- but a screen with fewer than two frames per image cannot keep up and is flagged there.

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
| `MID_BLOCK_REST_AFTER` | `None` | A rest follows this trial in every block; `None` centres it on the movements |
| `COND_NAMES` | 7 body parts | The movements, one trial each per block (see Advanced use) |
| `TRIGGER_INPUT_METHOD` | `'key'` | `'key'`, `'parallel'`, or `'serial'` |
| `TRIGGER_VALUE` | `'5'` | Key or byte the scanner sends |
| `FULL_SCREEN` | `True` | Set `False` for windowed testing |

## Advanced use

**A different number of blocks.** Set `BLOCKS` to anything from 1 to 8; `src/run_orders.py` holds one preset order per movement for each. The scan lasts blocks × (9 × movements + 18) + 15 s with the default timings — 81 × blocks + 15 s for the seven default movements — and the run order dialog is unchanged. `python3 src/design.py` prints the exact figures. Fewer blocks means less precision, so 4 is the recommendation. Some block counts cannot meet every balance rule, and `src/run_orders.py` lists the exceptions at the top. With the seven default movements they are 1 block (pairs of consecutive movements cannot be balanced), 2 blocks (a movement cannot be both early and late) and 8 blocks (a pair may occur twice in a run). With a different number of movements the exceptions differ, and the generator works them out rather than assuming these.

**Different body regions.** Add or remove movements by editing `COND_NAMES` in `src/parameters.py`, then rebuild the run orders with `python3 tools/make_run_orders.py` and check them with `python3 src/test_schedule.py`. Nothing else needs editing: the cue is drawn as text (`MOVE <region>`), so there is no image to add, and the run order dialog lists whatever `src/run_orders.py` holds. Two things follow from the number of movements:

- **N movements give N run orders**, not always seven, and a block is N trials long, so the scan gets longer. `python3 src/design.py` prints the new length and measurement count.
- **The rest inside a block follows on its own.** `MID_BLOCK_REST_AFTER` is `None` by default, which centres it, `ceil(movements / 2)` — trial 4 of seven movements, trial 3 of five — so there is nothing to adjust when you change `COND_NAMES`. Set a trial number to place it yourself and the task refuses one leaving fewer than two movements on either side; `0` turns it off, though keeping it is worth about 10% on the movement-vs-rest contrast and holds the longest unbroken run of movements to 27 s at five movements against 45 s without. Placing it yourself changes which run orders the generator picks, so rebuild afterwards.
- **Balanced random has N! possible orders.** With the seven defaults that is 5040, and subjects 1 to 100 all get different orders. With five movements there are 120, and subjects start sharing orders early: 1 of the first 20 and 10 of the first 50.
- **Not every movement count works at every block count.** Seven, six and eight movements all work from 1 to 8 blocks. Five movements has no valid run order at 2 blocks, and the generator leaves that block count out of `src/run_orders.py` and says so as it runs. Set `BLOCKS` to one that was left out and the task refuses at startup, naming the counts it does have.

The OpenRecon container must be given the rebuilt `src/run_orders.py`, and the run order numbers on the protocol card change with it.

**Print the design.** `python3 src/design.py` prints the settings, the movement pace, the scan length, the number of measurements and every movement onset, for each preset run order. Read the pace off it rather than assuming: it is the trial length divided by `NUM_COUNTDOWN_IMAGES`, so `TR` and `TRs_per_trial` move it too. Add a run order (`python3 src/design.py 3`) to print just that one. This is the spec sheet for the scanner and for the OpenRecon container, which has to match the timings printed at the top.

**Rebuild the run orders.** Only needed if the movements or the rules change: `python3 tools/make_run_orders.py` rewrites `src/run_orders.py`. It needs numpy and scipy, which the PsychoPy `.venv` already has, and takes a few minutes. Its output is deterministic, and the OpenRecon container must be given the same file.

**Check it.** `python3 src/test_schedule.py` checks the run orders and the schedule for every block count, and `python3 src/test_timing.py` checks that the countdown holds its scheduled times. Neither they nor `design.py` need PsychoPy.

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
│   ├── test_schedule.py         Checks the run orders and the schedule
│   └── test_timing.py           Checks that the countdown holds its scheduled times
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

## Note

Parts of this code were developed using Claude, all efforts have been made to check for accuracy.
