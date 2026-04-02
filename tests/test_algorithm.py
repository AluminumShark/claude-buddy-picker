"""Deterministic tests for the buddy generation algorithm.

All expected values were cross-verified against the Node.js implementation
(buddy-reroll-v2.js) and the live Claude Code cli.js 2.1.90 output.
"""

import pytest

from buddy_picker.algorithm import (
    EYES, HATS, RARITIES, RARITY_RANK, RARITY_WEIGHTS, SPECIES, STAT_NAMES,
    Mulberry32, fnv1a, pick, roll_full, roll_rarity,
)


# ── FNV-1a ─────────────────────────────────────────────────────────────────────


class TestFNV1a:
    def test_empty_string(self):
        assert fnv1a("") == 2166136261  # FNV offset basis

    def test_known_value(self):
        assert fnv1a("test") == 2949673445

    def test_hello(self):
        assert fnv1a("hello") == 1335831723

    def test_salt(self):
        assert fnv1a("friend-2026-401") == 2304472304


# ── Mulberry32 PRNG ────────────────────────────────────────────────────────────


class TestMulberry32:
    def test_deterministic_sequence(self):
        rng = Mulberry32(12345)
        expected = [
            0.9797282677609473,
            0.3067522644996643,
            0.484205421525985,
            0.817934412509203,
            0.5094283693470061,
        ]
        for i, exp in enumerate(expected):
            got = rng()
            assert abs(got - exp) < 1e-15, f"Mismatch at index {i}: {got} != {exp}"

    def test_same_seed_same_output(self):
        a = Mulberry32(42)
        b = Mulberry32(42)
        for _ in range(20):
            assert a() == b()

    def test_different_seeds_differ(self):
        a = Mulberry32(1)
        b = Mulberry32(2)
        assert a() != b()

    def test_output_range(self):
        rng = Mulberry32(99999)
        for _ in range(1000):
            val = rng()
            assert 0.0 <= val < 1.0


# ── roll_full test vectors ─────────────────────────────────────────────────────

VECTORS = [
    {
        "uid": "6652ffdd-b34b-4130-94db-e02405ddd824",
        "rarity": "common",
        "species": "owl",
        "eye": EYES[4],  # @
        "hat": "none",
        "shiny": False,
        "stats": {"DEBUGGING": 43, "PATIENCE": 13, "CHAOS": 5, "WISDOM": 37, "SNARK": 62},
    },
    {
        "uid": "94e6d69a477890d2a19137b248c8a4d8c28b62c872382eeedacc3fd6534ed179",
        "rarity": "legendary",
        "species": "dragon",
        "eye": EYES[1],  # star
        "hat": "crown",
        "shiny": True,
        "stats": {"DEBUGGING": 83, "PATIENCE": 56, "CHAOS": 83, "WISDOM": 100, "SNARK": 51},
    },
    {
        "uid": "test-user-abc",
        "rarity": "common",
        "species": "cat",
        "eye": EYES[3],  # circle
        "hat": "none",
        "shiny": False,
        "stats": {"DEBUGGING": 42, "PATIENCE": 73, "CHAOS": 1, "WISDOM": 37, "SNARK": 26},
    },
    {
        "uid": "aaaa",
        "rarity": "common",
        "species": "duck",
        "eye": EYES[4],  # @
        "hat": "none",
        "shiny": False,
        "stats": {"DEBUGGING": 69, "PATIENCE": 29, "CHAOS": 21, "WISDOM": 42, "SNARK": 1},
    },
    {
        "uid": "zzzz",
        "rarity": "uncommon",
        "species": "octopus",
        "eye": EYES[5],  # degree
        "hat": "halo",
        "shiny": False,
        "stats": {"DEBUGGING": 50, "PATIENCE": 75, "CHAOS": 11, "WISDOM": 18, "SNARK": 53},
    },
]


class TestRollFull:
    @pytest.mark.parametrize("vec", VECTORS, ids=[v["uid"][:20] for v in VECTORS])
    def test_vector(self, vec):
        result = roll_full(vec["uid"])
        assert result["rarity"] == vec["rarity"]
        assert result["species"] == vec["species"]
        assert result["eye"] == vec["eye"]
        assert result["hat"] == vec["hat"]
        assert result["shiny"] == vec["shiny"]
        assert result["stats"] == vec["stats"]


# ── Property tests ─────────────────────────────────────────────────────────────


class TestProperties:
    def test_common_always_no_hat(self):
        import secrets

        for _ in range(500):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            if b["rarity"] == "common":
                assert b["hat"] == "none"

    def test_stats_in_range(self):
        import secrets

        for _ in range(500):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            for name in STAT_NAMES:
                assert 1 <= b["stats"][name] <= 100, f"{name}={b['stats'][name]} out of range"

    def test_species_in_list(self):
        import secrets

        for _ in range(200):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            assert b["species"] in SPECIES

    def test_eye_in_list(self):
        import secrets

        for _ in range(200):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            assert b["eye"] in EYES

    def test_hat_in_list(self):
        import secrets

        for _ in range(200):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            assert b["hat"] in HATS

    def test_rarity_distribution(self):
        """Verify rarity distribution roughly matches weights over many rolls."""
        import secrets

        counts = {r: 0 for r in RARITIES}
        n = 10000
        for _ in range(n):
            uid = secrets.token_hex(32)
            b = roll_full(uid)
            counts[b["rarity"]] += 1

        for r in RARITIES:
            expected_pct = RARITY_WEIGHTS[r]
            actual_pct = counts[r] / n * 100
            assert abs(actual_pct - expected_pct) < 5, (
                f"{r}: expected ~{expected_pct}%, got {actual_pct:.1f}%"
            )
