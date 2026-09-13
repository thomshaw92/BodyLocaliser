"""Check that the countdown holds its scheduled times, without PsychoPy or a screen.

Run from the project root:  python3 src/test_timing.py

PsychoPy is stubbed out and time is virtual, so this runs anywhere and takes no
time. Holding each countdown image for a fixed time after its flip adds that
flip's latency to the epoch, and the error accumulates over a run: at the flip
cost measured below, a 4-block run overruns by about 1.5 s and needs an extra
volume. Holding each image to an absolute target does not. This checks that the
scheduled times are met, and that the fixed-wait pattern would still fail.
"""
import logging
import sys
import types

# What a flip costs beyond the wait. Measured on a scanner stimulus PC, where a 9 s
# screen of 12 images ran 0.036 to 0.043 s long. Machines differ a lot: a 120 Hz display
# measured 0.101 s per screen, a full frame per flip. This is a calibration knob, set to
# the gentler of the two; raising it only widens the gap the fixed-wait pattern shows.
FLIP_COST = 0.040 / 12
TOLERANCE = 1 / 60.0        # one refresh at 60 Hz: an onset may be a frame late, not more
now = 0.0


def flip():
    """A real win.flip() with waitBlanking blocks until the display is ready."""
    global now
    now += FLIP_COST


def wait(seconds):
    global now
    now += seconds


class Clock:
    def __init__(self):
        self.zero = now

    def getTime(self):
        return now - self.zero


# ---- stub PsychoPy before importing the task code -------------------------
core = types.ModuleType("psychopy.core")
core.Clock, core.wait, core.quit = Clock, wait, lambda: None
visual = types.ModuleType("psychopy.visual")
visual.Window = type("Window", (), {"flip": staticmethod(flip)})
visual.TextStim = visual.ImageStim = type("Stim", (), {"draw": lambda self: None})
psychopy = types.ModuleType("psychopy")
psychopy.core, psychopy.visual = core, visual
psychopy.event = types.ModuleType("psychopy.event")
psychopy.event.getKeys = lambda **kw: []     # nobody presses Escape, and no scanner here
psychopy.gui = types.ModuleType("psychopy.gui")
for name, mod in [("psychopy", psychopy), ("psychopy.core", core), ("psychopy.visual", visual),
                  ("psychopy.event", psychopy.event), ("psychopy.gui", psychopy.gui)]:
    sys.modules[name] = mod

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from functions import _display_countdown                                    # noqa: E402
from parameters import BLOCKS, NUM_COUNTDOWN_IMAGES, TR                     # noqa: E402
from schedule import generate_trial_schedule, measurements, run_order_blocks  # noqa: E402


def fixed_wait_countdown(win, images, display_time, overlay_text, clock, start, end):
    """A fixed wait after each flip, which drifts. Kept as the case to measure against."""
    for img in images:
        win.flip()
        wait(display_time)


def run(countdown):
    """Play a whole run and return (onsets, end time), all on one clock."""
    global now
    now = 0.0
    win, stim = visual.Window(), visual.TextStim()
    images = [visual.ImageStim() for _ in range(NUM_COUNTDOWN_IMAGES)]
    schedule = generate_trial_schedule(run_order_blocks(1, subnum=1))
    clock = Clock()
    onsets = []
    for entry in schedule:
        onset = clock.getTime()
        onsets.append(onset)
        countdown(win, images, (entry["duration"]) / len(images), stim, clock,
                  onset, entry["simulated_onset"] + entry["duration"])
    return schedule, onsets, clock.getTime()


def scheduled_countdown(win, images, display_time, overlay_text, clock, start, end):
    return _display_countdown(win, images, overlay_text, clock, start, end)


schedule, onsets, end = run(scheduled_countdown)
_, drift_onsets, drift_end = run(fixed_wait_countdown)
scheduled = [e["simulated_onset"] for e in schedule]
planned = schedule[-1]["simulated_onset"] + schedule[-1]["duration"]
worst = max(abs(a - b) for a, b in zip(onsets, scheduled))
drift_worst = max(abs(a - b) for a, b in zip(drift_onsets, scheduled))

# Every onset stays within one refresh of the schedule, and the error does not grow.
assert worst < TOLERANCE, f"onset off by {worst:.3f} s, more than one refresh"
assert abs(end - planned) < TOLERANCE, f"run ended {end - planned:+.3f} s off"
assert round(end / TR) == round(planned / TR), "the run no longer fits its measurements"
# The fixed-wait case has to be worse, or this check is not measuring anything. Its error
# grows with the number of epochs, which is the point; whether that crosses a volume boundary
# depends on how long the run is, so it is reported rather than asserted.
assert drift_worst > TOLERANCE, "the fixed-wait pattern did not drift; check FLIP_COST"
assert drift_end - planned > 0.5 * len(schedule) * NUM_COUNTDOWN_IMAGES * FLIP_COST, \
    "the fixed-wait pattern did not accumulate; check FLIP_COST"

# ---------------------------------------------------------------------------
# Recording the scanner triggers
# ---------------------------------------------------------------------------
# The scanner pulses at the start of each TR. These are queued as if they were key
# presses, so the recorder can be checked without a scanner or a serial port.
pending = []
psychopy.event.getKeys = lambda keyList=None, timeStamped=None, **kw: [
    (k, t) for k, t in [pending.pop(0) for _ in range(len(pending))]
    if keyList is None or k in keyList
]
psychopy.event.clearEvents = lambda *a, **kw: pending.clear()

from functions import TriggerLog, wait_for_trigger, wait_until             # noqa: E402

now = 0.0
clock = Clock()

# A press from before the operator was ready must not be taken as the first trigger:
# wait_for_trigger has to discard what is already waiting and take the next pulse.
polls = [0]


def arm(keyList=None, timeStamped=None, **kw):
    polls[0] += 1
    if polls[0] == 2:                        # a real pulse arrives while we wait
        pending.append(("5", 4.0))
    out = [(k, t) for k, t in pending if keyList is None or k in keyList]
    pending.clear()
    return out


psychopy.event.getKeys = arm
pending.append(("5", 0.0))                   # the stale one
triggers = TriggerLog(clock, "key", "5")
wait_for_trigger(triggers)
assert triggers.times == [4.0], f"started on a stale trigger: {triggers.times}"

psychopy.event.getKeys = lambda keyList=None, timeStamped=None, **kw: [
    (k, t) for k, t in [pending.pop(0) for _ in range(len(pending))]
    if keyList is None or k in keyList
]
triggers.times.clear()

# Pulses at every TR through a run of epochs, each polled inside the wait.
expected = [i * TR for i in range(1, 13)]
queue = list(expected)
for step in range(1, 7):                      # six 3 s epochs, 18 s in total
    target = step * 3.0
    while queue and queue[0] <= target:       # the scanner pulses during the wait
        pending.append(("5", queue.pop(0)))
    wait_until(target, clock, triggers)
assert triggers.times == expected, f"recorded {triggers.times}, expected {expected}"

# Being late must not stop the recording: the target is already past here.
pending.append(("5", now))
wait_until(now - 5.0, clock, triggers)
assert len(triggers.times) == len(expected) + 1, "a late epoch skipped its poll"

# ---------------------------------------------------------------------------
# The parallel trigger, which no hardware here can exercise
# ---------------------------------------------------------------------------
# Pin 10 is read from a script of 1s and 0s, so the rising edge is tested exactly.
# A pulse narrower than the poll interval, about 0.5 ms, falls between polls and is
# missed; real scanner pulses are milliseconds wide.
parallel = types.ModuleType("psychopy.parallel")


class ScriptedPort:
    def __init__(self, address=None):
        self.values, self.i = [], 0

    def readPin(self, pin):
        assert pin == 10, f"read pin {pin}, expected 10"
        v = self.values[min(self.i, len(self.values) - 1)]
        self.i += 1
        return v


logging.getLogger("functions").setLevel(logging.ERROR)   # two cases start high on purpose
parallel.ParallelPort = ScriptedPort
psychopy.parallel = parallel
sys.modules["psychopy.parallel"] = parallel

for label, values, expect in [
    ("held high across polls is one trigger", [0, 1, 1, 1, 1, 1, 0, 0], 1),
    ("two separate pulses", [0, 1, 1, 0, 0, 1, 1, 0], 2),
    ("line already high when the run starts", [1, 1, 1, 1, 0, 0, 0, 0], 0),
    ("already high, then a real pulse", [1, 1, 1, 0, 0, 1, 1, 0], 1),
    ("line stuck high throughout", [1, 1, 1, 1, 1, 1, 1, 1], 0),
]:
    log = TriggerLog(Clock(), "parallel", None, port_address=0x0378)
    log._port.values = values
    log.flush()
    log._port.i = 1                       # flush consumed the first read
    for _ in range(len(values) - 1):
        log.poll()
    assert len(log.times) == expect, f"parallel, {label}: {len(log.times)} not {expect}"

print(f"OK: {BLOCKS} blocks, {len(schedule)} epochs, {measurements(schedule)} measurements planned")
print(f"  scheduled targets: ends {end - planned:+.3f} s off {planned:.1f} s, "
      f"worst onset {worst:.3f} s off")
print(f"  fixed wait:        ends {drift_end - planned:+.3f} s off, worst onset {drift_worst:.3f} s off, "
      f"{round(drift_end / TR) - round(planned / TR):+d} measurements")
print(f"  triggers:          {len(triggers.times)} recorded, stale ones flushed, none missed when late")
print("  parallel port:     rising edge only, no false start on a line already high")
