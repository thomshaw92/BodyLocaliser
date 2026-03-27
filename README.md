# BodyLocaliser

A PsychoPy-based fMRI motor-imagery localiser. Participants are cued to move (or attempt to move) seven body parts while BOLD data is acquired. The task produces AFNI-compatible `.1D` onset files and CSV logs ready for first-level analysis.

## Conditions

Left Elbow, Right Elbow, Left Hand, Right Hand, Left Foot, Right Foot, Tongue.

Each condition appears once per block in a randomised order. Default: 2 blocks, 9 s trials, 9 s rest periods.

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

A dialog will ask for participant initials, subject number, and run number. Press `5` (or whatever `TRIGGER_VALUE` is set to) to start after the scanner begins. Press `Escape` at any time to abort -- partial data is still saved.

## Configuration

All tuneable settings live in `src/parameters.py`:

| Parameter | Default | Description |
|---|---|---|
| `TR` | 1.5 | Repetition time (seconds) |
| `TRs_per_trial` | 6 | Trial duration in TRs |
| `TRs_rest` | 6 | Rest duration in TRs |
| `TRs_dummy_scans` | 0 | Dummy scans before first trial |
| `BLOCKS` | 2 | Number of experimental blocks |
| `COND_NAMES` | 7 body parts | Conditions (one trial each per block) |
| `TRIGGER_INPUT_METHOD` | `'key'` | `'key'`, `'parallel'`, or `'serial'` |
| `TRIGGER_VALUE` | `'5'` | Key or byte the scanner sends |
| `FULL_SCREEN` | `True` | Set `False` for windowed testing |

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
│   └── parameters.py            All configurable settings
├── assets/                      Non-code resources
│   ├── images/                  Countdown timer images (1--12)
│   └── *.mp4                    Participant instruction video
├── data/                        Output (created at runtime, gitignored)
└── build/                       PyInstaller build configuration
```

## License

BSD 3-Clause. See `LICENSE`.
