"""
Reusable functions for the BodyLocaliser experiment.

All display, trigger, and I/O helpers live here so that main.py stays
focused on experiment flow.
"""

import os
import sys
import logging

from psychopy import visual, core, event, gui

from parameters import (
    BACKGROUND_COLOR,
    COUNTDOWN_IMAGE_POSITION,
    COUNTDOWN_IMAGE_SIZE,
    FIXATION_TEXT_SIZE,
    FULL_SCREEN,
    INSTRUCTION_TEXT_SIZE,
    NUM_COUNTDOWN_IMAGES,
    TEXT_COLOR,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resource helpers
# ---------------------------------------------------------------------------

def project_root() -> str:
    """Return the project root directory.

    When running from source, this is the parent of the ``src/`` directory.
    When running from a PyInstaller bundle, it is ``sys._MEIPASS``.
    """
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path: str) -> str:
    """Return the absolute path to a project resource.

    Paths are resolved relative to the project root, e.g.
    ``resource_path("assets/images/1.png")``.
    """
    return os.path.join(project_root(), relative_path)


# ---------------------------------------------------------------------------
# Window and visual stimuli
# ---------------------------------------------------------------------------

def create_window() -> visual.Window:
    """Create and return the fullscreen PsychoPy window."""
    return visual.Window(
        fullscr=FULL_SCREEN,
        screen=0,
        color=BACKGROUND_COLOR,
        colorSpace="rgb",
        units="height",
        waitBlanking=True,
    )


def load_countdown_images(win: visual.Window) -> list:
    """Load the numbered countdown images (1.png .. N.png) as ImageStim objects."""
    images = []
    for i in range(1, NUM_COUNTDOWN_IMAGES + 1):
        path = resource_path(os.path.join("assets", "images", f"{i}.png"))
        img = visual.ImageStim(
            win, image=path, size=COUNTDOWN_IMAGE_SIZE, pos=COUNTDOWN_IMAGE_POSITION
        )
        images.append(img)
    return images


# ---------------------------------------------------------------------------
# Subject information
# ---------------------------------------------------------------------------

def get_subject_info() -> dict:
    """Show a dialog to collect participant initials, subject number, and run number.

    Returns a dict with keys 'initials', 'subject_number', 'run_number'.
    Calls core.quit() if the user cancels the dialog.
    """
    while True:
        dlg = gui.Dlg(title="Subject Information")
        dlg.addText(
            "Instructions: press Escape at any time during the experiment to quit."
        )
        dlg.addField("Participant Initials:")
        dlg.addField("Subject Number:")
        dlg.addField("Run Number:")
        data = dlg.show()

        if not dlg.OK:
            core.quit()

        initials = data[0].strip()
        raw_sub = data[1].strip()
        raw_run = data[2].strip()

        if not initials:
            print("Error: Participant Initials cannot be empty.")
            continue
        try:
            sub = int(raw_sub)
        except ValueError:
            print(f"Error: Subject Number '{raw_sub}' must be a valid integer.")
            continue
        try:
            run = int(raw_run)
        except ValueError:
            print(f"Error: Run Number '{raw_run}' must be a valid integer.")
            continue

        return {"initials": initials, "subject_number": sub, "run_number": run}


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------

def wait_for_trigger(
    input_method: str = "key",
    trigger_value: str = "5",
    port_address=None,
    serial_port=None,
) -> None:
    """Block until a scanner trigger is received.

    Supported *input_method* values:
      - ``'key'``      -- waits for a keyboard press (default; for bench testing)
      - ``'parallel'`` -- reads pin 10 of a parallel port
      - ``'serial'``   -- reads bytes from a serial port at 9600 baud
    """
    if input_method == "key":
        logger.info("Waiting for key press: %s", trigger_value)
        event.waitKeys(keyList=[trigger_value])
        logger.info("Trigger received (key press)")

    elif input_method == "parallel":
        if port_address is None:
            raise ValueError("port_address is required for parallel trigger input.")
        from psychopy import parallel  # imported here -- not available on every platform

        pp = parallel.ParallelPort(address=port_address)
        logger.info("Waiting for parallel port trigger at %s ...", port_address)
        while not pp.readPin(10):
            core.wait(0.001)
        logger.info("Trigger received (parallel port)")

    elif input_method == "serial":
        if serial_port is None:
            raise ValueError("serial_port is required for serial trigger input.")
        import serial as pyserial  # imported here -- not available on every platform

        ser = pyserial.Serial(serial_port, 9600, timeout=1)
        logger.info("Waiting for serial port trigger on %s ...", serial_port)
        while True:
            if ser.in_waiting > 0:
                signal = ser.read().decode("utf-8")
                if signal == trigger_value:
                    break
            core.wait(0.001)
        logger.info("Trigger received (serial port)")

    else:
        raise ValueError(
            f"Invalid trigger input_method '{input_method}'. "
            "Choose 'key', 'parallel', or 'serial'."
        )


# ---------------------------------------------------------------------------
# Quit handler
# ---------------------------------------------------------------------------

def check_quit_key() -> None:
    """Check whether Escape has been pressed and exit gracefully if so."""
    if "escape" in event.getKeys():
        logger.info("Experiment terminated by user (Escape).")
        core.quit()


# ---------------------------------------------------------------------------
# Instruction / fixation screens
# ---------------------------------------------------------------------------

def show_instruction(win: visual.Window, TR: float, TRs_instruction: int) -> None:
    """Display the task instruction screen for the given duration."""
    text = visual.TextStim(
        win,
        text="Please move\n\nor attempt to move\n\nthe body part instructed on the screen",
        color=TEXT_COLOR,
        height=INSTRUCTION_TEXT_SIZE,
        units="height",
    )
    text.draw()
    win.flip()
    core.wait(TR * TRs_instruction)


def show_waiting_for_scanner(win: visual.Window) -> None:
    """Display 'Waiting for scanner' until the trigger arrives."""
    text = visual.TextStim(
        win,
        text="Waiting for scanner",
        color=TEXT_COLOR,
        height=INSTRUCTION_TEXT_SIZE,
        units="height",
    )
    text.draw()
    win.flip()


def show_fixation(
    win: visual.Window, TR: float, TRs_duration: int, text: str = "REST"
) -> None:
    """Show a simple text fixation for *TRs_duration* TRs."""
    stim = visual.TextStim(
        win, text=text, color=TEXT_COLOR, height=FIXATION_TEXT_SIZE, units="height"
    )
    for _ in range(TRs_duration):
        stim.draw()
        win.flip()
        core.wait(TR)


def handle_dummy_scans(
    win: visual.Window, TR: float, TRs_dummy_scans: int
) -> None:
    """Display fixation during dummy scans (skipped when TRs_dummy_scans == 0)."""
    if TRs_dummy_scans > 0:
        show_fixation(win, TR, TRs_dummy_scans, text="REST")


# ---------------------------------------------------------------------------
# Countdown display
# ---------------------------------------------------------------------------

def _display_countdown(
    win: visual.Window,
    images: list,
    display_time: float,
    overlay_text: visual.TextStim,
) -> None:
    """Cycle through countdown images with a text overlay."""
    for img in images:
        img.draw()
        overlay_text.draw()
        win.flip()
        core.wait(display_time)


def run_trial(
    win: visual.Window,
    condition: str,
    TR: float,
    TRs_per_trial: int,
    countdown_images: list,
    global_clock: core.Clock,
) -> tuple:
    """Run a single motor-imagery trial.

    Returns (onset_time, duration) measured from *global_clock*.
    """
    trial_text = visual.TextStim(
        win,
        text=f"MOVE {condition}",
        color=TEXT_COLOR,
        height=INSTRUCTION_TEXT_SIZE,
        units="height",
    )

    trial_duration = TR * TRs_per_trial
    display_time = trial_duration / len(countdown_images)

    onset_time = global_clock.getTime()
    logger.debug("Trial %s started at %.3f s", condition, onset_time)

    _display_countdown(win, countdown_images, display_time, trial_text)

    end_time = global_clock.getTime()
    logger.debug("Trial %s ended at %.3f s", condition, end_time)

    return onset_time, end_time - onset_time


def show_rest_with_countdown(
    win: visual.Window,
    TR: float,
    TRs_duration: int,
    countdown_images: list,
) -> None:
    """Display a REST screen with the countdown timer."""
    rest_text = visual.TextStim(
        win,
        text="REST",
        color=TEXT_COLOR,
        height=FIXATION_TEXT_SIZE,
        units="height",
    )
    rest_duration = TR * TRs_duration
    display_time = rest_duration / len(countdown_images)
    _display_countdown(win, countdown_images, display_time, rest_text)
