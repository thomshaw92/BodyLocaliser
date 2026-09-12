"""Build the preset run orders and write src/run_orders.py.

Run from the project root:  python3 tools/make_run_orders.py
Needs numpy and scipy, which the PsychoPy .venv already has. Takes a few minutes.
Output is deterministic: the same movements and timings give the same file.

RUN_ORDERS[blocks][k] is preset run order k (1 to 7) for that many blocks; each block shows
every movement in src/parameters.py once. Run order k is one base run with every movement
index shifted by k - 1, mod 7, so across the 7 orders each movement fills each place of each
block exactly once and each opens exactly one run order.

Rules inside a run:
  - a block never starts with the movement that ended the previous block
  - no ordered pair of consecutive movements occurs twice; with every step (the gap between
    two movements in the list, mod 7) used exactly `blocks` times, which also gives each
    ordered pair exactly `blocks` occurrences across the 7 orders
  - each movement is in the first three places of one block and the last three of another
Three block counts cannot meet all of them; the exceptions are noted in the file written:
  - 1 block: no ordering of 7 movements uses all 6 steps, so pairs cannot be balanced
  - 2 blocks: the movement in the middle place of a block cannot be both early and late, so
    the rule becomes "not in the same third of the block twice"
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
from parameters import (BLOCKS, COND_NAMES, MID_BLOCK_REST_AFTER, TR,  # noqa: E402
                        TRs_final_rest, TRs_per_trial, TRs_rest)

N = len(COND_NAMES)
BLOCK_COUNTS = range(1, 9)
EPOCH, REST, FINAL_REST = TR * TRs_per_trial, TR * TRs_rest, TR * TRs_final_rest
EARLY = (N - 1) // 2                      # places 0 to 2 are early, 3 is middle, 4 to 6 late
SEED, WANT, NODES_PER_TRY, NODES_PER_COUNT = 42, 2000, 2_000_000, 20_000_000
SHORT = ["".join(w[0] for w in n.split()) if " " in n else n[:2] for n in COND_NAMES]


def transitions(run):
    return [(a, b) for block in run for a, b in zip(block, block[1:])]


def third(place):
    return 0 if place < EARLY else 1 if place == EARLY else 2


def rules_ok(run):
    """The boundary and place rules; the search itself enforces the pair and step rules."""
    if any(run[i][-1] == run[i + 1][0] for i in range(len(run) - 1)):
        return False
    places = [[block.index(c) for block in run] for c in range(N)]
    if len(run) >= 3:
        return all(min(p) < EARLY and max(p) > EARLY for p in places)
    if len(run) == 2:
        return all(third(p[0]) != third(p[1]) for p in places)
    return True


def search_bases(blocks, rng):
    """Bases found by depth-first search with random restarts, in a fixed node budget, so
    the result depends on the seed and not on how fast this machine is."""
    if blocks == 1:                        # pairs cannot be balanced: any ordering will do
        return [[list((0,) + p)] for p in itertools.permutations(range(1, N))]

    limit = 1 if 6 * blocks <= N * (N - 1) else 2
    bases, budget_left = [], NODES_PER_COUNT

    def grow(run, block, pairs, steps, nodes):
        nodes[0] -= 1
        if nodes[0] <= 0:
            return None
        if len(block) == N:
            run = run + [block]
            if len(run) == blocks:
                return run if rules_ok(run) else None
            for start in rng.sample(range(N), N):
                if start != block[-1]:
                    found = grow(run, [start], pairs, steps, nodes)
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
            found = grow(run, block + [v], pairs, steps, nodes)
            if found:
                return found
            steps[step] += 1
            pairs[(u, v)] -= 1
        return None

    while len(bases) < WANT and budget_left > 0:
        nodes = [min(NODES_PER_TRY, budget_left)]
        base = grow([], [0], Counter(), [blocks] * N, nodes)
        budget_left -= min(NODES_PER_TRY, budget_left) - max(nodes[0], 0)
        if base:
            bases.append(base)
    return bases


def onsets(run):
    """Movement onsets in seconds from the first TR, and the length of the run."""
    ons, t = defaultdict(list), REST
    for block in run:
        for place, c in enumerate(block):
            ons[c].append(t)
            t += EPOCH
            if place + 1 == MID_BLOCK_REST_AFTER:
                t += REST
        t += REST
    return ons, t - REST + FINAL_REST


# AFNI BLOCK4(d,1): a d-second boxcar convolved with t^4 exp(-t), scaled to peak 1.
def block_hrf(t):
    return gammainc(5, np.clip(t, 0, None)) - gammainc(5, np.clip(t - EPOCH, 0, None))


PEAK = block_hrf(np.arange(0, 40, 0.0005)).max()
EYE = np.eye(N)
PAIRS = list(itertools.combinations(range(N), 2))
CONTRASTS = np.vstack([EYE, EYE - (1 - EYE) / (N - 1),              # 7 vs rest, 7 vs other six,
                       [EYE[i] - EYE[j] for i, j in PAIRS]])        # 21 pairwise
OTHERS = slice(N, 2 * N)
MODELS = {}


def model(blocks):
    """Time points and drift regressors for a run of this many blocks."""
    if blocks not in MODELS:
        _, total = onsets([list(range(N))] * blocks)
        T = np.arange(round(total / TR)) * TR
        drift = np.polynomial.legendre.legvander(2 * T / T[-1] - 1, 1 + int(total // 150))
        MODELS[blocks] = (T, drift, total)
    return MODELS[blocks]


def nsd(run):
    """Normalised SD of each contrast, sqrt(diag(C (X'X)^-1 C')), as 3dDeconvolve -nodata prints."""
    T, drift, _ = model(len(run))
    ons, _ = onsets(run)
    stim = np.column_stack([sum(block_hrf(T - o) for o in ons[c]) / PEAK for c in range(N)])
    X = np.hstack([drift, stim])
    V = np.linalg.inv(X.T @ X)[-N:, -N:]
    return np.sqrt(np.einsum("ij,jk,ik->i", CONTRASTS, V, CONTRASTS))


def check_set(orders):
    blocks = len(orders[0])
    limit = 1 if 6 * blocks <= N * (N - 1) else 2
    assert all(rules_ok(r) for r in orders), "a run order breaks a within-run rule"
    assert all(max(Counter(transitions(r)).values(), default=0) <= limit
               for r in orders), "an ordered pair repeats within a run"
    cells = Counter((b, place, c) for r in orders
                    for b, block in enumerate(r) for place, c in enumerate(block))
    assert len(cells) == blocks * N * N and set(cells.values()) == {1}, "block places unbalanced"
    pairs = Counter(t for r in orders for t in transitions(r))
    if blocks > 1:
        assert len(pairs) == N * (N - 1) and set(pairs.values()) == {blocks}, "pairs unbalanced"


def main():
    out = {}
    print(f"{len(COND_NAMES)} movements, {EPOCH:.0f} s each; rest {REST:.0f} s after movement "
          f"{MID_BLOCK_REST_AFTER} and after each block; final rest {FINAL_REST:.0f} s\n")
    for blocks in BLOCK_COUNTS:
        started = time.time()
        bases = search_bases(blocks, random.Random(SEED + blocks))
        if not bases:
            raise SystemExit(f"No valid base run found for {blocks} blocks.")
        base = min(bases, key=lambda r: nsd(r)[OTHERS].max())
        orders = [[[(c + k) % N for c in block] for block in base] for k in range(N)]
        check_set(orders)
        out[blocks] = {k: [[COND_NAMES[c] for c in block] for block in r]
                       for k, r in enumerate(orders, 1)}

        E = np.array([nsd(r) for r in orders])
        _, total = onsets(orders[0])
        print(f"{blocks} block{'s' if blocks > 1 else ' '}: {total:4.0f} s, "
              f"{round(total / TR):3d} measurements, {len(bases):3d} bases in {time.time() - started:5.1f} s;"
              f"  vs rest {E[:, :N].min():.4f}-{E[:, :N].max():.4f}"
              f"  vs other six {E[:, OTHERS].min():.4f}-{E[:, OTHERS].max():.4f}"
              f"  worst pairwise {E[:, 2 * N:].max():.4f}")

    print(f"\nrun orders for the {BLOCKS} blocks set in parameters.py:")
    for k, order in out[BLOCKS].items():
        print(f"{k:>9}  " + " | ".join(" ".join(SHORT[COND_NAMES.index(c)] for c in block)
                                       for block in order))

    (ROOT / "src" / "run_orders.py").write_text(
        '"""BodyLocaliser run orders, written by tools/make_run_orders.py. Do not edit by hand.\n\n'
        "RUN_ORDERS[blocks][k] is preset run order k (1 to 7) for that many blocks: a list of\n"
        "blocks, each listing the movements in the order they are shown. Across the 7 orders each\n"
        "movement fills each place of each block exactly once, each opens exactly one run order,\n"
        "and each ordered pair of consecutive movements occurs exactly `blocks` times. Exceptions:\n"
        "  - 1 block: pairs cannot be balanced, because no ordering of the 7 movements uses all\n"
        "    6 steps; some pairs occur twice across the 7 orders and some never\n"
        "  - 2 blocks: each movement is in a different third of the block in the two blocks,\n"
        "    rather than early in one block and late in another\n"
        "  - 8 blocks: an ordered pair may occur twice within a run, because its 48 transitions\n"
        '    outnumber the 42 ordered pairs\n"""\n\nRUN_ORDERS = '
        + pprint.pformat(out, width=110) + "\n")


if __name__ == "__main__":
    main()
