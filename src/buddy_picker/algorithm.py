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

_RARITY_TOTAL = sum(RARITY_WEIGHTS.values())

# ── Cached ctypes converter for hot path ──────────────────────────────────────

_c32 = ctypes.c_int32


def _imul(a: int, b: int) -> int:
    """Emulate JavaScript Math.imul (signed 32-bit multiply)."""
    return _c32((_c32(a).value * _c32(b).value) & 0xFFFFFFFF).value


def _unsigned_rshift(val: int, shift: int) -> int:
    """Emulate JavaScript >>> (unsigned right shift)."""
    return (val & 0xFFFFFFFF) >> shift


# ── FNV-1a hash ────────────────────────────────────────────────────────────────


def fnv1a(s: str) -> int:
    """FNV-1a 32-bit hash. Matches cli.js when running on Node / claude.exe."""
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


# ── Mulberry32 PRNG ────────────────────────────────────────────────────────────


class Mulberry32:
    """Mulberry32 PRNG with exact JavaScript signed-integer semantics."""

    __slots__ = ("a",)

    def __init__(self, seed: int):
        self.a = seed & 0xFFFFFFFF

    def __call__(self) -> float:
        c = _c32
        a = c(self.a).value
        a = c(a + 0x6D2B79F5).value
        self.a = a & 0xFFFFFFFF
        t = _imul(a ^ ((a & 0xFFFFFFFF) >> 15), 1 | a)
        t2 = _imul(t ^ ((t & 0xFFFFFFFF) >> 7), 61 | t)
        t = c(t + t2).value ^ t
        return ((t ^ ((t & 0xFFFFFFFF) >> 14)) & 0xFFFFFFFF) / 4294967296


# ── Roll helpers ───────────────────────────────────────────────────────────────


def pick(rng: Mulberry32, arr: list):
    return arr[int(rng() * len(arr))]


def roll_rarity(rng: Mulberry32) -> str:
    roll = rng() * _RARITY_TOTAL
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
    """Generate all buddy attributes from a userID string."""
    rng = Mulberry32(fnv1a(uid + SALT))
    rarity = roll_rarity(rng)
    species = pick(rng, SPECIES)
    eye = pick(rng, EYES)
    hat = "none" if rarity == "common" else pick(rng, HATS)
    shiny = rng() < 0.01
    stats = roll_stats(rng, rarity)
    return {
        "rarity": rarity, "species": species, "eye": eye,
        "hat": hat, "shiny": shiny, "stats": stats,
    }


# ── Inlined fast search function ──────────────────────────────────────────────

# Pre-compute for inline use
_RARITY_CUM = []
_cum = 0
for _r in RARITIES:
    _cum += RARITY_WEIGHTS[_r]
    _RARITY_CUM.append((_cum, _r))
del _cum, _r

_N_SPECIES = len(SPECIES)
_N_EYES = len(EYES)
_N_HATS = len(HATS)
_N_STATS = len(STAT_NAMES)


def roll_filtered(
    uid: str, *,
    min_rank: int = 0,
    species: str | None = None,
    eye: str | None = None,
    hat: str | None = None,
    shiny: bool = False,
    min_stats: int | None = None,
) -> dict | None:
    """Inlined roll with early-exit. Returns None if filters don't match.

    Uses min_rank (int) instead of min_rarity (str) to avoid dict lookup per call.
    """
    c = _c32
    M = 0xFFFFFFFF

    # ── Inline FNV-1a ──
    h = 2166136261
    for ch in uid:
        h ^= ord(ch)
        h = (h * 16777619) & M
    # hash the salt too
    for ch in SALT:
        h ^= ord(ch)
        h = (h * 16777619) & M

    # ── Inline PRNG (no closure — avoids function-object overhead) ──
    _st = [h & M]  # mutable container for PRNG state

    def _next(_st=_st, _c=c, _M=M):
        a = _c(_st[0]).value
        a = _c(a + 0x6D2B79F5).value
        _st[0] = a & _M
        t = _imul(a ^ ((a & _M) >> 15), 1 | a)
        t2 = _imul(t ^ ((t & _M) >> 7), 61 | t)
        t = _c(t + t2).value ^ t
        return ((t ^ ((t & _M) >> 14)) & _M) / 4294967296

    # ── Roll rarity ──
    roll = _next() * _RARITY_TOTAL
    rarity = "common"
    rarity_rank = 0
    for i, (cum, r) in enumerate(_RARITY_CUM):
        if roll < cum:
            rarity = r
            rarity_rank = i
            break
    if min_rank and rarity_rank < min_rank:
        return None

    # ── Roll species ──
    sp = SPECIES[int(_next() * _N_SPECIES)]
    if species and sp != species:
        return None

    # ── Roll eye ──
    ey = EYES[int(_next() * _N_EYES)]
    if eye and ey != eye:
        return None

    # ── Roll hat ──
    if rarity == "common":
        ht = "none"
    else:
        ht = HATS[int(_next() * _N_HATS)]
    if hat and ht != hat:
        return None

    # ── Roll shiny ──
    sh = _next() < 0.01
    if shiny and not sh:
        return None

    # ── Roll stats (only reached if all filters passed so far) ──
    floor = RARITY_FLOOR[rarity]
    peak_idx = int(_next() * _N_STATS)
    dump_idx = int(_next() * _N_STATS)
    while dump_idx == peak_idx:
        dump_idx = int(_next() * _N_STATS)

    stats = {}
    for i, name in enumerate(STAT_NAMES):
        if i == peak_idx:
            stats[name] = min(100, floor + 50 + int(_next() * 30))
        elif i == dump_idx:
            stats[name] = max(1, floor - 10 + int(_next() * 15))
        else:
            stats[name] = floor + int(_next() * 40)

    if min_stats and not all(v >= min_stats for v in stats.values()):
        return None

    return {
        "rarity": rarity, "species": sp, "eye": ey,
        "hat": ht, "shiny": sh, "stats": stats,
    }
