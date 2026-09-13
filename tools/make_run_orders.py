"""Build the preset run orders and write src/run_orders.py.

Run from the project root:  python3 tools/make_run_orders.py
Needs numpy and scipy, which the PsychoPy .venv already has. Takes a few minutes.
Output is deterministic: the same movements and timings give the same file.

To change the movements, edit COND_NAMES in src/parameters.py and rerun this, then run
python3 src/test_schedule.py and give the OpenRecon container the new src/run_orders.py.
N movements give N run orders, and the run order dialog offers one for each.

RUN_ORDERS[blocks][k] is preset run order k (1 to N) for that many blocks; each block shows
every movement in src/parameters.py once. Run order k is one base run with every movement
index shifted by k - 1, mod N, so across the N orders each movement fills each place of each
block exactly once and each opens exactly one run order.

Rules inside a run:
  - a block never starts with the movement that ended the previous block
  - no ordered pair of consecutive movements occurs twice; with every step (the gap between
    two movements in the list, mod N) used exactly `blocks` times, which also gives each
    ordered pair exactly `blocks` occurrences across the N orders
  - each movement is in the early places of one block and the late places of another
Not every block count can meet all of them. A run spreads blocks * (N - 1) transitions over
N * (N - 1) ordered pairs, so a pair must repeat once blocks > N; where the pair rule cannot
be met the limit is relaxed one step at a time, and where no run exists at all that block
count is left out of the file. Whatever was relaxed is written into it. At 7 movements:
  - 1 block: the steps are not balanced, so pairs are not balanced either
  - 2 blocks: the movement in the middle place of a block cannot be both early and late, so
    the rule becomes "not in the same one of early / middle / late twice"
  - 8 blocks: 48 transitions exceed the 42 ordered pairs, so a pair may occur twice
Of the bases found, the one whose worst movement-vs-mean-of-the-other-six contrast (the
analysis contrast) has the lowest AFNI normalised SD is kept, as 3dDeconvolve -nodata reports
it: BLOCK(9,1), the timings from parameters.py, AFNI's default polort.
"""
import itertools
import pprint
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.special import gammainc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from parameters import (BLOCKS, COND_NAMES, TR,  # noqa: E402
                        TRs_final_rest, TRs_per_trial, TRs_rest)
from schedule import MID_REST  # noqa: E402  -- resolves a MID_BLOCK_REST_AFTER of None

N = len(COND_NAMES)
BLOCK_COUNTS = range(1, 9)
EPOCH, REST, FINAL_REST = TR * TRs_per_trial, TR * TRs_rest, TR * TRs_final_rest
EARLY = (N - 1) // 2                      # places 0 to 2 are early, 3 is middle, 4 to 6 late
SEED, WANT, NODES_PER_TRY, NODES_PER_COUNT = 42, 2000, 2_000_000, 20_000_000
SHORT = ["".join(w[0] for w in n.split()) if " " in n else n[:2] for n in COND_NAMES]


def transitions(run):
    return [(a, b) for block in run for a, b in zip(block, block[1:])]


def rules_ok(run):
    """The boundary and place rules; the search itself enforces the pair and step rules."""
    if any(run[i][-1] == run[i + 1][0] for i in range(len(run) - 1)):
        return False
    places = [[block.index(c) for block in run] for c in range(N)]
    if len(run) >= 3:
        return all(min(p) < EARLY and max(p) > EARLY for p in places)
    if len(run) == 2:          # not in the same one of early / middle / late twice
        return all((p[0] < EARLY, p[0] > EARLY) != (p[1] < EARLY, p[1] > EARLY) for p in places)
    return True


def search_bases(blocks, rng):
    """Bases found by depth-first search with random restarts, in a fixed node budget, so
    the result depends on the seed and not on how fast this machine is.

    Returns (bases, limit). *limit* is how often an ordered pair of consecutive movements
    is allowed to repeat within one run. A run has blocks * (N - 1) transitions to spread
    over the N * (N - 1) ordered pairs, so ceil(blocks / N) is the arithmetic floor; the
    floor is not always reachable once the step, boundary and place rules are added, so the
    limit is relaxed one step at a time until a base exists. Returns ([], 0) if none does.
    """
    if blocks == 1:                        # pairs cannot repeat: each movement appears once
        return [[list((0,) + p)] for p in itertools.permutations(range(1, N))], 1

    bases, used, try_start, limit = [], 0, 0, 0

    def grow(run, block, pairs, steps):
        nonlocal used
        used += 1
        if used - try_start >= NODES_PER_TRY:
            return None
        if len(block) == N:
            run = run + [block]
            if len(run) == blocks:
                return run if rules_ok(run) else None
            for start in rng.sample(range(N), N):
                if start != block[-1]:
                    found = grow(run, [start], pairs, steps)
                    if found:
                        return found
            return None
        u = block[-1]
        for v in rng.sample(range(N), N):
            step = (v - u) % N
            if v in block or steps[step] == 0 or pairs[(u, v)] >= limit:
                continue
            steps[step] -= 1
            pairs[(u, v)] += 1
            found = grow(run, block + [v], pairs, steps)
            if found:
                return found
            steps[step] += 1
            pairs[(u, v)] -= 1
        return None

    for limit in range(-(-blocks // N), blocks + 1):
        bases, used = [], 0
        while len(bases) < WANT and used < NODES_PER_COUNT:
            try_start = used
            base = grow([], [0], Counter(), [blocks] * N)
            if base:
                bases.append(base)
        if bases:
            return bases, limit
    return [], 0


def onsets(run):
    """Movement onsets in seconds from the first TR, and the length of the run."""
    ons, t = defaultdict(list), REST
    for block in run:
        for place, c in enumerate(block):
            ons[c].append(t)
            t += EPOCH
            if place + 1 == MID_REST:
                t += REST
        t += REST
    return ons, t - REST + FINAL_REST


# AFNI BLOCK4(d,1): a d-second boxcar convolved with t^4 exp(-t), scaled to peak 1.
def block_hrf(t):
    return gammainc(5, np.clip(t, 0, None)) - gammainc(5, np.clip(t - EPOCH, 0, None))


PEAK = block_hrf(np.arange(0, 40, 0.0005)).max()
EYE = np.eye(N)
CONTRASTS = np.vstack([EYE, EYE - (1 - EYE) / (N - 1)])   # each vs rest, then vs the other N-1
OTHERS = slice(N, 2 * N)
PAIRWISE = np.array([EYE[i] - EYE[j] for i, j in itertools.combinations(range(N), 2)])
MODELS = {}


def model(blocks):
    """Time points and drift regressors for a run of this many blocks."""
    if blocks not in MODELS:
        _, total = onsets([list(range(N))] * blocks)
        T = np.arange(round(total / TR)) * TR
        drift = np.polynomial.legendre.legvander(2 * T / T[-1] - 1, 1 + int(total // 150))
        MODELS[blocks] = (T, drift, total)
    return MODELS[blocks]


def nsd(run, contrasts=CONTRASTS):
    """Normalised SD of each contrast, sqrt(diag(C (X'X)^-1 C')), as 3dDeconvolve -nodata prints."""
    T, drift, _ = model(len(run))
    ons, _ = onsets(run)
    stim = np.column_stack([sum(block_hrf(T - o) for o in ons[c]) / PEAK for c in range(N)])
    X = np.hstack([drift, stim])
    V = np.linalg.inv(X.T @ X)[-N:, -N:]
    return np.sqrt(np.einsum("ij,jk,ik->i", contrasts, V, contrasts))


def check_set(orders, limit):
    blocks = len(orders[0])
    assert all(rules_ok(r) for r in orders), "a run order breaks a within-run rule"
    assert all(max(Counter(transitions(r)).values(), default=0) <= limit
               for r in orders), "an ordered pair repeats within a run"
    cells = Counter((b, place, c) for r in orders
                    for b, block in enumerate(r) for place, c in enumerate(block))
    assert len(cells) == blocks * N * N and set(cells.values()) == {1}, "block places unbalanced"
    pairs = Counter(t for r in orders for t in transitions(r))
    if blocks > 1:
        assert len(pairs) == N * (N - 1) and set(pairs.values()) == {blocks}, "pairs unbalanced"


def exceptions(out, limits):
    """The rules each block count could not meet, in the words the written file uses."""
    lines = []
    for blocks in sorted(out):
        if blocks == 1:
            seen = Counter(t for r in out[1].values() for t in transitions(r))
            lines.append(f"  - 1 block: the steps between consecutive movements are not balanced, so\n"
                         f"    across the {N} orders an ordered pair occurs up to {max(seen.values())} "
                         f"times and {N * (N - 1) - len(seen)} never occur")
        if blocks == 2:
            lines.append("  - 2 blocks: each movement is in a different one of early, middle and late\n"
                         "    in the two blocks, rather than early in one block and late in another")
        if limits[blocks] > 1:
            often = "twice" if limits[blocks] == 2 else f"{limits[blocks]} times"
            lines.append(f"  - {blocks} blocks: an ordered pair may occur {often} within a run, because "
                         f"its\n    {blocks * (N - 1)} transitions outnumber the {N * (N - 1)} "
                         f"ordered pairs")
    for blocks in sorted(set(BLOCK_COUNTS) - set(out)):
        lines.append(f"  - {blocks} blocks: no run order can meet the rules with {N} movements, so\n"
                     f"    this block count is absent")
    return lines


def main():
    out, limits = {}, {}
    print(f"{len(COND_NAMES)} movements, {EPOCH:.0f} s each; rest {REST:.0f} s after movement "
          f"{MID_REST} and after each block; final rest {FINAL_REST:.0f} s\n")
    for blocks in BLOCK_COUNTS:
        started = time.time()
        bases, limit = search_bases(blocks, random.Random(SEED + blocks))
        if not bases:
            print(f"{blocks} block{'s' if blocks > 1 else ' '}: no run order meets the rules with "
                  f"{N} movements; left out of run_orders.py ({time.time() - started:.1f} s)")
            continue
        base = min(bases, key=lambda r: nsd(r)[OTHERS].max())
        orders = [[[(c + k) % N for c in block] for block in base] for k in range(N)]
        check_set(orders, limit)
        out[blocks], limits[blocks] = {k: [[COND_NAMES[c] for c in block] for block in r]
                                       for k, r in enumerate(orders, 1)}, limit

        E = np.array([nsd(r) for r in orders])
        worst_pair = max(nsd(r, PAIRWISE).max() for r in orders)
        total = model(blocks)[2]
        print(f"{blocks} block{'s' if blocks > 1 else ' '}: {total:4.0f} s, "
              f"{round(total / TR):3d} measurements, {len(bases):3d} bases in {time.time() - started:5.1f} s;"
              f"  pair limit {limit}"
              f"  vs rest {E[:, :N].min():.4f}-{E[:, :N].max():.4f}"
              f"  vs other {N - 1} {E[:, OTHERS].min():.4f}-{E[:, OTHERS].max():.4f}"
              f"  worst pairwise {worst_pair:.4f}")

    if not out:
        raise SystemExit(f"No block count works with {N} movements; nothing written.")

    if BLOCKS in out:
        print(f"\nrun orders for the {BLOCKS} blocks set in parameters.py:")
        for k, order in out[BLOCKS].items():
            print(f"{k:>9}  " + " | ".join(" ".join(SHORT[COND_NAMES.index(c)] for c in block)
                                           for block in order))
    else:
        print(f"\nparameters.py asks for {BLOCKS} blocks, which could not be built; set BLOCKS "
              f"to one of {', '.join(str(b) for b in sorted(out))}.")

    (ROOT / "src" / "run_orders.py").write_text(
        '"""BodyLocaliser run orders, written by tools/make_run_orders.py. Do not edit by hand.\n\n'
        f"RUN_ORDERS[blocks][k] is preset run order k (1 to {N}) for that many blocks: a list of\n"
        f"blocks, each listing the movements in the order they are shown. Across the {N} orders each\n"
        "movement fills each place of each block exactly once, each opens exactly one run order,\n"
        "and each ordered pair of consecutive movements occurs exactly `blocks` times. Exceptions:\n"
        + "\n".join(exceptions(out, limits))
        + '\n"""\n\nRUN_ORDERS = '
        + pprint.pformat(out, width=110) + "\n")


if __name__ == "__main__":
    main()
