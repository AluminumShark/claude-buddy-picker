"""CLI entry point for buddy-picker."""

import argparse
import io
import os
import secrets
import sys
import time

from buddy_picker.algorithm import (
    EYES, HATS, RARITIES, RARITY_RANK, RARITY_WEIGHTS, SPECIES, STAT_NAMES,
    roll_filtered, roll_full,
)
from buddy_picker.config import apply_uid, get_current_uid, restore_uid
from buddy_picker.display import (
    HAT_DISPLAY, RARITY_COLOR, RARITY_ICON, SPECIES_EMOJI, c, display_buddy,
)

# ── Platform setup ─────────────────────────────────────────────────────────────


def _platform_init() -> None:
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        os.system("")  # enable ANSI escape sequences on Windows


# ── Search ─────────────────────────────────────────────────────────────────────


def _worker_init():
    """Ignore SIGINT in workers — let the parent handle Ctrl+C."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _search_chunk(args):
    """Worker: search a chunk and return hits."""
    chunk_size, min_rank, species, eye, hat, shiny_req, min_stats = args
    hits = []
    for _ in range(chunk_size):
        uid = secrets.token_hex(32)
        b = roll_filtered(
            uid, min_rank=min_rank, species=species, eye=eye,
            hat=hat, shiny=shiny_req, min_stats=min_stats,
        )
        if b is not None:
            hits.append((uid, b))
    return hits


def search(
    species=None, min_rarity=None, eye=None, hat=None,
    shiny=False, min_stats=None, count=5, max_iter=50_000_000,
    progress=True,
):
    import multiprocessing as mp

    min_rank = RARITY_RANK.get(min_rarity, 0) if min_rarity else 0
    n_workers = max(1, (mp.cpu_count() or 1))
    chunk = max(20_000, max_iter // (n_workers * 20))
    results = []
    start = time.time()
    total_checked = 0
    worker_args = (chunk, min_rank, species, eye, hat, shiny, min_stats)

    try:
        with mp.Pool(n_workers, initializer=_worker_init) as pool:
            while total_checked < max_iter and len(results) < count:
                n_batches = min(n_workers, (max_iter - total_checked + chunk - 1) // chunk)
                if n_batches <= 0:
                    break

                for hits in pool.imap_unordered(_search_chunk, [worker_args] * n_batches):
                    results.extend(hits)
                    total_checked += chunk

                    if progress:
                        for uid, b in hits:
                            display_buddy(b, uid, compact=True)

                    if len(results) >= count:
                        break

                    now = time.time()
                    if progress and now - start > 3:
                        elapsed = now - start
                        rate = total_checked / elapsed
                        print(f"  ... {total_checked:,} checked ({rate:,.0f}/s, "
                              f"{len(results)} found)", file=sys.stderr)

            pool.terminate()
    except KeyboardInterrupt:
        print("\n  Interrupted.")

    results = results[:count]
    elapsed = time.time() - start
    if progress:
        print(f"\n  Searched {total_checked:,} in {elapsed:.1f}s, found {len(results)}"
              f" ({n_workers} workers)")

    return results


# ── Interactive helpers ────────────────────────────────────────────────────────


def prompt_choice(label, options, allow_any=True):
    """Let user pick from a list. Returns None for 'any'."""
    print(f"\n  {c(label, '1')}")
    if allow_any:
        print(f"    {c('0', '36')}) any")
    for i, opt in enumerate(options, 1):
        print(f"    {c(str(i), '36')}) {opt}")

    while True:
        raw = input("\n  > ").strip()
        if not raw:
            return None if allow_any else options[0]
        if raw == "0" and allow_any:
            return None
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            for opt in options:
                if raw.lower() in str(opt).lower():
                    return opt
        print("  Invalid choice, try again.")


def _estimate_odds(species, min_rarity, eye, hat, shiny, min_stats):
    prob = 1.0
    if min_rarity:
        rarity_prob = sum(
            RARITY_WEIGHTS[r] for r in RARITIES if RARITY_RANK[r] >= RARITY_RANK[min_rarity]
        ) / 100
        prob *= rarity_prob
    if species:
        prob *= 1 / len(SPECIES)
    if eye:
        prob *= 1 / len(EYES)
    if hat and min_rarity and min_rarity != "common":
        prob *= 1 / len(HATS)
    if shiny:
        prob *= 0.01
    if min_stats:
        prob *= 0.001
    return prob


# ── Interactive mode ───────────────────────────────────────────────────────────


def interactive():
    print(c("\n  === Claude Code Buddy Picker ===\n", "1;36"))

    species_opts = [f"{SPECIES_EMOJI.get(s, '?')} {s}" for s in SPECIES]
    choice = prompt_choice("Species:", species_opts)
    species = SPECIES[species_opts.index(choice)] if choice else None

    rarity_opts = [f"{RARITY_ICON[r]} {r} ({RARITY_WEIGHTS[r]}%)" for r in RARITIES]
    choice = prompt_choice("Minimum rarity:", rarity_opts)
    min_rarity = RARITIES[rarity_opts.index(choice)] if choice else None

    eye_opts = [f"  {e}  " for e in EYES]
    choice = prompt_choice("Eye style:", eye_opts)
    eye = EYES[eye_opts.index(choice)] if choice else None

    hat_opts = [HAT_DISPLAY[h] for h in HATS]
    choice = prompt_choice("Hat:", hat_opts)
    hat = HATS[hat_opts.index(choice)] if choice else None

    shiny_choice = prompt_choice("Shiny?", ["yes", "no"], allow_any=False)
    shiny = shiny_choice == "yes"

    min_stats = None
    raw = input(f"\n  {c('Minimum ALL stats (0 = any):', '1')} ").strip()
    if raw and raw != "0":
        try:
            min_stats = int(raw)
        except ValueError:
            pass

    count = 5
    raw = input(f"\n  {c('How many results? [5]:', '1')} ").strip()
    if raw:
        try:
            count = int(raw)
        except ValueError:
            pass

    prob = _estimate_odds(species, min_rarity, eye, hat, shiny, min_stats)
    expected = int(1 / prob) if prob > 0 else 999999999
    max_iter = min(max(expected * count * 3, 1_000_000), 500_000_000)

    print(f"\n  {c('Estimated odds:', '2')} ~1 in {expected:,}")
    print(f"  {c('Max iterations:', '2')} {max_iter:,.0f}")
    print(f"\n  {c('Searching...', '1;33')}\n")

    results = search(
        species=species, min_rarity=min_rarity, eye=eye, hat=hat,
        shiny=shiny, min_stats=min_stats, count=count, max_iter=int(max_iter),
    )

    if not results:
        print("  No matches found. Try relaxing your criteria.")
        return

    _prompt_apply(results)


# ── Hierarchical mode ─────────────────────────────────────────────────────────


def hierarchical():
    print(c("\n  === Buddy Picker (Step-by-Step) ===\n", "1;36"))

    rarity_opts = [f"{RARITY_ICON[r]} {r} ({RARITY_WEIGHTS[r]}%)" for r in RARITIES]
    choice = prompt_choice("Step 1 - Rarity:", rarity_opts, allow_any=False)
    rarity = RARITIES[rarity_opts.index(choice)]

    species_opts = [f"{SPECIES_EMOJI.get(s, '?')} {s}" for s in SPECIES]
    choice = prompt_choice("Step 2 - Species:", species_opts, allow_any=False)
    species = SPECIES[species_opts.index(choice)]

    eye_opts = [f"  {e}  " for e in EYES]
    choice = prompt_choice("Step 3 - Eye:", eye_opts, allow_any=False)
    eye = EYES[eye_opts.index(choice)]

    if rarity == "common":
        print(f"\n  {c('Step 4 - Hat:', '1')} (common rarity = no hat)")
        hat = "none"
    else:
        hat_opts = [HAT_DISPLAY[h] for h in HATS]
        choice = prompt_choice("Step 4 - Hat:", hat_opts, allow_any=False)
        hat = HATS[hat_opts.index(choice)]

    shiny_choice = prompt_choice("Step 5 - Shiny?", ["yes", "no"], allow_any=False)
    shiny = shiny_choice == "yes"

    count = 10
    raw = input(f"\n  {c('How many to find? [10]:', '1')} ").strip()
    if raw:
        try:
            count = int(raw)
        except ValueError:
            pass

    prob = _estimate_odds(species, rarity, eye, hat, shiny, None)
    expected = int(1 / prob) if prob > 0 else 999999999
    max_iter = min(max(expected * count * 3, 1_000_000), 500_000_000)

    emoji = SPECIES_EMOJI.get(species, "")
    shiny_label = " shiny" if shiny else ""
    label = f"Looking for {RARITY_ICON[rarity]} {rarity} {emoji} {species}, eye={eye}, hat={hat}{shiny_label}"
    print(f"\n  {c(label, '1;33')}")
    odds_label = f"Odds: ~1 in {expected:,} | Max: {max_iter:,.0f}"
    print(f"  {c(odds_label, '2')}\n")

    results = search(
        species=species, min_rarity=rarity, eye=eye, hat=hat,
        shiny=shiny, count=count, max_iter=int(max_iter),
    )

    if not results:
        print("  No matches found. The odds were against us!")
        return

    results.sort(key=lambda x: sum(x[1]["stats"].values()), reverse=True)

    print(f"\n  {c(f'Found {len(results)} - sorted by total stats:', '1')}\n")
    for i, (uid, b) in enumerate(results, 1):
        total = sum(b["stats"].values())
        stats_brief = " ".join(f"{k[:3]}:{v}" for k, v in b["stats"].items())
        print(f"    {c(str(i), '36')}) total={total} | {stats_brief}")

    print(f"    {c('0', '36')}) cancel")
    print(f"    {c('v1-v' + str(len(results)), '36')}) view full card (e.g. v1)")

    while True:
        raw = input("\n  > ").strip().lower()
        if raw == "0":
            print("  Cancelled.")
            return
        if raw.startswith("v"):
            try:
                idx = int(raw[1:])
                if 1 <= idx <= len(results):
                    display_buddy(results[idx - 1][1], results[idx - 1][0])
                    continue
            except ValueError:
                pass
        try:
            idx = int(raw)
            if 1 <= idx <= len(results):
                uid, buddy = results[idx - 1]
                display_buddy(buddy, uid)
                confirm = input("  Apply this buddy? (y/n) ").strip().lower()
                if confirm in ("y", "yes"):
                    apply_uid(uid)
                    print(c("\n  Done! Restart Claude Code and run /buddy.\n", "1;32"))
                else:
                    print("  Cancelled.")
                return
        except ValueError:
            pass
        print("  Invalid. Enter a number or v<number>.")


# ── Shared apply prompt ───────────────────────────────────────────────────────


def _prompt_apply(results):
    print(f"\n  {c('Pick a buddy to apply:', '1')}")
    for i, (uid, b) in enumerate(results, 1):
        rc = RARITY_COLOR[b["rarity"]]
        shiny_tag = " shiny" if b["shiny"] else ""
        hat_tag = f" {b['hat']}" if b["hat"] != "none" else ""
        peak = max(b["stats"], key=b["stats"].get)
        print(f"    {c(str(i), '36')}) {SPECIES_EMOJI.get(b['species'], '?')} "
              f"{c(b['rarity'], rc)} {b['species']}{shiny_tag}"
              f" eye={b['eye']}{hat_tag} | {peak}={b['stats'][peak]}")

    print(f"    {c('0', '36')}) cancel")

    while True:
        raw = input("\n  > ").strip()
        if raw == "0":
            print("  Cancelled.")
            return
        try:
            idx = int(raw)
            if 1 <= idx <= len(results):
                uid, buddy = results[idx - 1]
                display_buddy(buddy, uid)
                confirm = input("  Apply this buddy? (y/n) ").strip().lower()
                if confirm in ("y", "yes"):
                    apply_uid(uid)
                    print(c("\n  Done! Restart Claude Code and run /buddy.\n", "1;32"))
                return
        except ValueError:
            pass
        print("  Invalid choice.")


# ── CLI entry point ────────────────────────────────────────────────────────────


def main():
    _platform_init()

    parser = argparse.ArgumentParser(
        description="Claude Code /buddy pet picker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  buddy-picker                          # Interactive mode
  buddy-picker --hierarchical           # Step-by-step
  buddy-picker --check                  # Show current buddy
  buddy-picker --restore                # Restore original userID
  buddy-picker --species dragon --rarity legendary --shiny
  buddy-picker --species cat --eye @ --hat crown --count 10
""",
    )
    parser.add_argument("--check", action="store_true", help="show current buddy")
    parser.add_argument("--restore", action="store_true", help="restore original userID")
    parser.add_argument("--hierarchical", action="store_true", help="step-by-step drill-down")
    parser.add_argument("--species", choices=SPECIES, help="target species")
    parser.add_argument("--rarity", choices=RARITIES, help="minimum rarity")
    parser.add_argument("--eye", choices=EYES, help="eye style", metavar="EYE")
    parser.add_argument("--hat", choices=HATS, help="hat type")
    parser.add_argument("--shiny", action="store_true", help="require shiny")
    parser.add_argument("--min-stats", type=int, help="require ALL stats >= value", metavar="N")
    parser.add_argument("--count", type=int, default=5, help="results to find (default: 5)")
    parser.add_argument("--max", type=int, default=50_000_000, help="max iterations")
    parser.add_argument("--apply", type=int, help="auto-apply result N (1-indexed)", metavar="N")

    args = parser.parse_args()

    if args.check:
        uid = get_current_uid()
        if not uid:
            print("  No userID found in ~/.claude.json")
            return
        print(f"\n  Current userID: {uid[:24]}...")
        display_buddy(roll_full(uid), uid)
        return

    if args.restore:
        restore_uid()
        return

    if args.hierarchical:
        hierarchical()
        return

    has_filters = any([args.species, args.rarity, args.eye, args.hat, args.shiny, args.min_stats])
    if not has_filters:
        interactive()
        return

    # CLI search mode
    filters = []
    if args.species:
        filters.append(f"species={args.species}")
    if args.rarity:
        filters.append(f"rarity>={args.rarity}")
    if args.eye:
        filters.append(f"eye={args.eye}")
    if args.hat:
        filters.append(f"hat={args.hat}")
    if args.shiny:
        filters.append("shiny")
    if args.min_stats:
        filters.append(f"stats>={args.min_stats}")

    print(f"\n  {c('Searching:', '1')} {', '.join(filters)}")
    print(f"  {c('Max:', '2')} {args.max:,} | {c('Count:', '2')} {args.count}\n")

    results = search(
        species=args.species, min_rarity=args.rarity, eye=args.eye, hat=args.hat,
        shiny=args.shiny, min_stats=args.min_stats, count=args.count, max_iter=args.max,
    )

    if not results:
        print("\n  No matches found.")
        return

    if args.apply and 1 <= args.apply <= len(results):
        uid, buddy = results[args.apply - 1]
        display_buddy(buddy, uid)
        apply_uid(uid)
        print(c("  Done! Restart Claude Code and run /buddy.\n", "1;32"))
        return

    _prompt_apply(results)
