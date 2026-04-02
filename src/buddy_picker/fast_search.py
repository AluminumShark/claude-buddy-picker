"""Numba JIT-accelerated seed-space scanner.

Enumerates integer seeds 0..2^32 directly, running only the Mulberry32 PRNG
(no FNV-1a hash, no string generation). Uses prange for automatic parallelism.
"""

import numpy as np
from numba import njit, prange
from numba.typed import List as NumbaList


@njit(cache=True)
def _mulberry32(state):
    """One Mulberry32 PRNG step. Returns (new_state, float_value)."""
    a = np.int32(np.uint32(state))
    a = np.int32(a + np.int32(0x6D2B79F5))
    new_state = np.uint32(a)

    # t = Math.imul(a ^ a >>> 15, 1 | a)
    au = np.uint32(a)
    t = np.int32(np.int32(a ^ np.int32(au >> np.uint32(15))) * np.int32(np.int32(1) | a))

    # t = (t + Math.imul(t ^ t >>> 7, 61 | t)) ^ t
    tu = np.uint32(t)
    t2 = np.int32(np.int32(t ^ np.int32(tu >> np.uint32(7))) * np.int32(np.int32(61) | t))
    t = np.int32(np.int32(t + t2) ^ t)

    # (t ^ t >>> 14) >>> 0 / 4294967296
    tu2 = np.uint32(t)
    val = np.float64(np.uint32(t ^ np.int32(tu2 >> np.uint32(14)))) / 4294967296.0

    return new_state, val


@njit(parallel=True, cache=True)
def scan_seeds_range(start, end, min_rarity_cum, species_idx, eye_idx, hat_idx, need_shiny):
    """Scan seed range [start, end). Returns list of matching seed integers.

    Args:
        start, end: seed range (uint32)
        min_rarity_cum: cumulative weight threshold (0.0=any, 60.0=uncommon+, 85.0=rare+, 95.0=epic+, 99.0=legendary)
        species_idx: target species index in SPECIES array (-1 = any)
        eye_idx: target eye index (-1 = any)
        hat_idx: target hat index (-1 = any, 0 = none explicitly)
        need_shiny: require shiny (bool)
    """
    results = NumbaList()
    # Pre-add a dummy then clear, so numba infers the type
    results.append(np.uint32(0))
    results.clear()

    for seed in prange(start, end):
        state = np.uint32(seed)

        # Roll rarity
        state, val = _mulberry32(state)
        roll = val * 100.0
        if min_rarity_cum > 0.0 and roll < min_rarity_cum:
            continue

        # Determine actual rarity for hat logic
        is_common = roll < 60.0

        # Roll species
        state, val = _mulberry32(state)
        if species_idx >= 0 and np.int32(val * 18.0) != species_idx:
            continue

        # Roll eye
        state, val = _mulberry32(state)
        if eye_idx >= 0 and np.int32(val * 6.0) != eye_idx:
            continue

        # Roll hat (only for non-common)
        if not is_common:
            state, val = _mulberry32(state)
            if hat_idx >= 0 and np.int32(val * 8.0) != hat_idx:
                continue
        else:
            # Common always gets hat=none (index 0)
            if hat_idx > 0:
                continue

        # Roll shiny
        state, val = _mulberry32(state)
        if need_shiny and val >= 0.01:
            continue

        results.append(np.uint32(seed))

    return results
