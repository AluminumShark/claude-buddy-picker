"""Core algorithm matching Claude Code cli.js 2.1.90.

Seed pipeline:  FNV-1a(userID + SALT) -> Mulberry32 PRNG -> weighted rolls.
"""

import ctypes

# ── Constants (exact match to cli.js 2.1.90) ──────────────────────────────────

SALT = "friend-2026-401"

SPECIES = [
    "duck", "goose", "blob", "cat", "dragon", "octopus", "owl", "penguin",
    "turtle", "snail", "ghost", "axolotl", "capybara", "cactus", "robot",
    "rabbit", "mushroom", "chonk",
]

RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]

RARITY_WEIGHTS = {"common": 60, "uncommon": 25, "rare": 10, "epic": 4, "legendary": 1}

RARITY_RANK = {r: i for i, r in enumerate(RARITIES)}

EYES = ["\u00b7", "\u2726", "\u00d7", "\u25c9", "@", "\u00b0"]

HATS = ["none", "crown", "tophat", "propeller", "halo", "wizard", "beanie", "tinyduck"]

STAT_NAMES = ["DEBUGGING", "PATIENCE", "CHAOS", "WISDOM", "SNARK"]

RARITY_FLOOR = {"common": 5, "uncommon": 15, "rare": 25, "epic": 35, "legendary": 50}

# ── Low-level helpers ──────────────────────────────────────────────────────────


def _imul(a: int, b: int) -> int:
    """Emulate JavaScript Math.imul (signed 32-bit multiply)."""
    a = ctypes.c_int32(a).value
    b = ctypes.c_int32(b).value
    return ctypes.c_int32((a * b) & 0xFFFFFFFF).value


def _unsigned_rshift(val: int, shift: int) -> int:
    """Emulate JavaScript >>> (unsigned right shift)."""
    return (val & 0xFFFFFFFF) >> shift


# ── FNV-1a hash ────────────────────────────────────────────────────────────────


def fnv1a(s: str) -> int:
    """FNV-1a 32-bit hash. Matches cli.js when running on Node / claude.exe."""
    h = 2166136261  # FNV offset basis
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF  # FNV prime
    return h


# ── Mulberry32 PRNG ────────────────────────────────────────────────────────────


class Mulberry32:
    """Mulberry32 PRNG with exact JavaScript signed-integer semantics."""

    def __init__(self, seed: int):
        self.a = seed & 0xFFFFFFFF

    def __call__(self) -> float:
        a = ctypes.c_int32(self.a).value
        a = ctypes.c_int32(a + 0x6D2B79F5).value
        self.a = a & 0xFFFFFFFF
        t = _imul(a ^ _unsigned_rshift(a, 15), 1 | a)
        t2 = _imul(t ^ _unsigned_rshift(t, 7), 61 | t)
        t = ctypes.c_int32(t + t2).value ^ t
        return _unsigned_rshift(t ^ _unsigned_rshift(t, 14), 0) / 4294967296


# ── Roll helpers ───────────────────────────────────────────────────────────────


def pick(rng: Mulberry32, arr: list):
    """Uniform random selection from *arr*."""
    return arr[int(rng() * len(arr))]


def roll_rarity(rng: Mulberry32) -> str:
    total = sum(RARITY_WEIGHTS.values())
    roll = rng() * total
    for r in RARITIES:
        roll -= RARITY_WEIGHTS[r]
        if roll < 0:
            return r
    return "common"


def roll_stats(rng: Mulberry32, rarity: str) -> dict[str, int]:
    floor = RARITY_FLOOR[rarity]
    peak = pick(rng, STAT_NAMES)
    dump = pick(rng, STAT_NAMES)
    while dump == peak:
        dump = pick(rng, STAT_NAMES)
    stats = {}
    for name in STAT_NAMES:
        if name == peak:
            stats[name] = min(100, floor + 50 + int(rng() * 30))
        elif name == dump:
            stats[name] = max(1, floor - 10 + int(rng() * 15))
        else:
            stats[name] = floor + int(rng() * 40)
    return stats


def roll_full(uid: str) -> dict:
    """Generate all buddy attributes from a userID string.

    Returns dict with keys: rarity, species, eye, hat, shiny, stats.
    """
    rng = Mulberry32(fnv1a(uid + SALT))
    rarity = roll_rarity(rng)
    species = pick(rng, SPECIES)
    eye = pick(rng, EYES)
    hat = "none" if rarity == "common" else pick(rng, HATS)
    shiny = rng() < 0.01
    stats = roll_stats(rng, rarity)
    return {
        "rarity": rarity,
        "species": species,
        "eye": eye,
        "hat": hat,
        "shiny": shiny,
        "stats": stats,
    }
