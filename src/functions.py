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
    BLOCKS,
    COUNTDOWN_IMAGE_POSITION,
    COUNTDOWN_IMAGE_SIZE,
    FIXATION_TEXT_SIZE,
    FULL_SCREEN,
    INSTRUCTION_TEXT_SIZE,
    NUM_COUNTDOWN_IMAGES,
    SCREEN,
    TEXT_COLOR,
    TRIAL_TEXT_SIZE,
)
from run_orders import RUN_ORDERS
from schedule import file_safe, trigger_byte

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
    """Create and return the PsychoPy window, with the mouse cursor hidden.

    PsychoPy shows the cursor again when the window closes.
    """
    win = visual.Window(
        fullscr=FULL_SCREEN,
        screen=SCREEN,
        color=BACKGROUND_COLOR,
        colorSpace="rgb",
        units="height",
        waitBlanking=True,
    )
    win.mouseVisible = False
    return win


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
    """Show a dialog to collect participant initials, subject number, and run number,
    then ask for the run order (see ask_run_order).

    Anything invalid is reported in red at the top of the dialog, which reopens
    with what was typed still in place. Returns a dict with keys 'initials',
    'subject_number', 'run_number', 'run_order'. Calls core.quit() if the user
    cancels either dialog.
    """
    error, typed = "", ["", "", ""]
    while True:
        dlg = gui.Dlg(title="Subject Information")
        if error:
            dlg.addText(error, color="red")
        dlg.addText(
            "Instructions: press Escape at any time during the experiment to quit."
        )
        dlg.addField("Participant Initials:", initial=typed[0])
        dlg.addField("Subject Number:", initial=typed[1])
        dlg.addField("Run Number:", initial=typed[2])
        data = dlg.show()

        if not dlg.OK:
            core.quit()

        typed = [str(data[i]).strip() for i in range(3)]
        initials, raw_sub, raw_run = typed

        if not initials:
            error = "Participant initials cannot be empty."
        elif not file_safe(initials):
            error = (f"Participant initials '{initials}' go into the output folder name, "
                     f"so use only letters, digits, spaces, - and _.")
        elif not raw_sub.isdecimal():
            error = f"Subject number '{raw_sub}' must be a whole number."
        elif not raw_run.isdecimal():
            error = f"Run number '{raw_run}' must be a whole number."
        else:
            return {
                "initials": initials,
                "subject_number": int(raw_sub),
                "run_number": int(raw_run),
                "run_order": ask_run_order(),
            }
        logger.error(error)


def ask_run_order():
    """Ask which run order to present: a preset OpenRecon order (returns 1 to the number
    of movements) or a balanced random order (returns "random").

    Nothing is preselected, so the operator has to choose; leaving it unchosen is
    reported in red in the dialog. Calls core.quit() if the user cancels it.
    """
    choices = {"Balanced random (seeded on subject number)": "random",
               **{f"OpenRecon run order {k}": k for k in sorted(RUN_ORDERS[BLOCKS])}}
    error = ""
    while True:
        dlg = gui.Dlg(title="Run order")
        if error:
            dlg.addText(error, color="red")
        dlg.addText("For OpenRecon, pick the run order set on the scanner protocol card.")
        dlg.addField("Run order:", choices=["Choose...", *choices])
        data = dlg.show()

        if not dlg.OK:
            core.quit()
        if data[0] in choices:
            return choices[data[0]]
        error = "Please choose a run order."
        logger.error(error)


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

        want = trigger_byte(trigger_value)
        if want is None:
            raise ValueError(f"trigger_value {trigger_value!r} is not a single byte.")
        ser = pyserial.Serial(serial_port, 9600, timeout=1)
        logger.info("Waiting for serial port trigger on %s ...", serial_port)
        while True:
            # Compared as raw bytes: a scanner pulse need not be text, and decoding
            # one that is not valid UTF-8 used to raise here, while waiting.
            if ser.in_waiting > 0 and ser.read() == want:
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


def show_waiting_for_scanner(win: visual.Window, detail: str = "") -> None:
    """Display 'Waiting for scanner', and *detail* below it, until the trigger arrives."""
    text = visual.TextStim(
        win,
        text=f"Waiting for scanner\n\n{detail}",
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
    clock = core.Clock()
    for i in range(1, TRs_duration + 1):
        stim.draw()
        win.flip()
        remaining = i * TR - clock.getTime()
        if remaining > 0:
            core.wait(remaining)


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
    overlay_text: visual.TextStim,
    clock: core.Clock,
    start: float,
    end: float,
) -> None:
    """Cycle through the countdown images between *start* and *end* on *clock*.

    Each image is held until its own absolute target time, so the latency of a
    flip is absorbed by the image it belongs to. Holding each image for a fixed
    time after its flip makes that latency cumulative instead, lengthening every
    epoch and the run with it.
    """
    step = (end - start) / len(images)
    for i, img in enumerate(images, start=1):
        check_quit_key()        # so Escape acts within one image, not one epoch
        img.draw()
        overlay_text.draw()
        win.flip()
        remaining = start + i * step - clock.getTime()
        if remaining > 0:
            core.wait(remaining)


def run_trial(
    win: visual.Window,
    condition: str,
    countdown_images: list,
    global_clock: core.Clock,
    end_time: float,
) -> float:
    """Run a single motor-imagery trial, ending at *end_time* on *global_clock*.

    *end_time* comes from the schedule, so a trial that starts late is shortened
    rather than pushing everything after it later. Returns the onset time.
    """
    trial_text = visual.TextStim(
        win,
        text=f"MOVE {condition}",
        color=TEXT_COLOR,
        height=TRIAL_TEXT_SIZE,
        units="height",
    )

    onset_time = global_clock.getTime()
    logger.debug("Trial %s started at %.3f s", condition, onset_time)

    _display_countdown(win, countdown_images, trial_text, global_clock, onset_time, end_time)

    logger.debug("Trial %s ended at %.3f s", condition, global_clock.getTime())
    return onset_time


def show_rest_with_countdown(
    win: visual.Window,
    countdown_images: list,
    global_clock: core.Clock,
    end_time: float,
) -> float:
    """Display a REST screen with the countdown, ending at *end_time* on *global_clock*.

    Returns the onset time.
    """
    rest_text = visual.TextStim(
        win,
        text="REST",
        color=TEXT_COLOR,
        height=FIXATION_TEXT_SIZE,
        units="height",
    )
    onset_time = global_clock.getTime()
    _display_countdown(win, countdown_images, rest_text, global_clock, onset_time, end_time)
    return onset_time
