# Claude Buddy Picker

Re-roll your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) `/buddy` companion pet. Pick any species, rarity, eyes, hat, shiny, and stats you want.

## How It Works

Claude Code generates your `/buddy` pet deterministically from your `userID`:

```
FNV-1a(userID + salt) -> Mulberry32 PRNG -> weighted attribute rolls
```

Same `userID` always produces the same pet. This tool exhaustively scans all 2^32 possible PRNG seeds using [Numba](https://numba.pydata.org/) JIT compilation, then reverse-engineers a valid `userID` for each match. A full scan of 4.3 billion seeds takes about 5-10 seconds.

## Installation

```bash
git clone https://github.com/AluminumShark/claude-buddy-picker.git
cd claude-buddy-picker
uv sync
```

Requires Python >= 3.10 and [uv](https://docs.astral.sh/uv/).

## Quick Start

```bash
# 1. Pick your buddy
uv run buddy-picker

# 2. Choose attributes interactively, select a result, confirm apply

# 3. Restart Claude Code and run /buddy
```

That's it. The tool writes the new `userID` to `~/.claude.json` and removes the old companion data so Claude Code re-hatches your pet on next startup.

## Usage

```bash
# Interactive mode - pick attributes step by step
uv run buddy-picker

# Direct CLI search (all filters are optional and combinable)
uv run buddy-picker --species dragon --rarity legendary --shiny --eye "✦" --hat crown

# Auto-apply the best result without prompts
uv run buddy-picker --species chonk --rarity legendary --shiny --apply 1

# Step-by-step drill-down mode
uv run buddy-picker --hierarchical

# Show your current buddy
uv run buddy-picker --check

# Restore your original userID
uv run buddy-picker --restore
```

## Example Output

```
$ uv run buddy-picker --species dragon --rarity legendary --shiny --count 3

  Scanned 4,294,967,296 seeds in 5.6s, found 511 matches
  ♛ LEGENDARY 🐉 dragon eye=✦ hat=crown SHINY
    DEBUGGING:85 PATIENCE:71 CHAOS:70 WISDOM:100 SNARK:41
    uid: b0dd1e000000000000000000000000000000000000000000000000004pvwpx0
  ...

  Total: 6.0s, 3 results
```

## Attributes

### Species (18, uniform random)

| | | | | | |
|---|---|---|---|---|---|
| duck | goose | blob | cat | dragon | octopus |
| owl | penguin | turtle | snail | ghost | axolotl |
| capybara | cactus | robot | rabbit | mushroom | chonk |

### Rarity (weighted)

| Rarity | Weight | Base Stats |
|--------|--------|------------|
| Common | 60% | 5 |
| Uncommon | 25% | 15 |
| Rare | 10% | 25 |
| Epic | 4% | 35 |
| Legendary | 1% | 50 |

### Eyes (6, uniform)

`·` `✦` `×` `◉` `@` `°`

### Hats (8, uniform — common always gets "none")

`none` `crown` `tophat` `propeller` `halo` `wizard` `beanie` `tinyduck`

### Shiny

1% chance.

### Stats

**DEBUGGING**, **PATIENCE**, **CHAOS**, **WISDOM**, **SNARK**

Each buddy has one peak stat (boosted) and one dump stat (reduced). Higher rarity = higher floor for all stats.

## CLI Options

```
--species NAME       Target species (duck, dragon, chonk, etc.)
--rarity NAME        Minimum rarity (common/uncommon/rare/epic/legendary)
--eye CHAR           Eye style (· ✦ × ◉ @ °)
--hat NAME           Hat type (none/crown/tophat/propeller/halo/wizard/beanie/tinyduck)
--shiny              Require shiny
--min-stats N        Require ALL stats >= N
--count N            Number of results to find (default: 5)
--apply N            Auto-apply the Nth result (no interactive prompt)
--check              Show current buddy from ~/.claude.json
--restore            Restore original userID from backup
--hierarchical       Step-by-step attribute selection mode
```

## How the Search Works

1. **Seed scan** — Numba JIT scans all 4,294,967,296 possible PRNG seeds (~5s on modern hardware), with early-exit filtering on rarity/species/eye/hat/shiny
2. **FNV-1a reverse** — For each matching seed, a meet-in-the-middle algorithm constructs a 64-char hex `userID` that hashes to that seed
3. **Apply** — Writes the `userID` to `~/.claude.json` and removes the `companion` block so Claude Code re-hatches on next launch

If Numba is not installed, falls back to a slower random brute-force search.

## Troubleshooting

### `/buddy` didn't change after applying

Claude Code reads `userID` from `~/.claude.json` to generate your buddy. If you have **multiple Claude Code installations**, the wrong one might be running.

Check which `claude` binary is active:

```bash
# Windows
where claude

# macOS / Linux
which claude
```

If you see multiple results (e.g. WinGet, npm, and pnpm), only the **pnpm version** is guaranteed to respect the `userID` field. Remove the others:

```bash
# Remove WinGet version (Windows)
winget uninstall Anthropic.ClaudeCode

# Remove npm version
npm uninstall -g @anthropic-ai/claude-code
```

After uninstalling, verify only pnpm remains, then re-run `buddy-picker` and restart Claude Code.

### Buddy shows the old pet even after apply

Claude Code caches companion data in `~/.claude.json`. The tool removes the `companion` block automatically, but if it persists, delete it manually:

1. Open `~/.claude.json`
2. Remove the entire `"companion": { ... }` block
3. Restart Claude Code and run `/buddy`

## Development

```bash
git clone https://github.com/AluminumShark/claude-buddy-picker.git
cd claude-buddy-picker
uv sync --dev
uv run pytest -v
uv run ruff check src/ tests/
```

## Compatibility

- Python >= 3.10
- Windows, macOS, Linux
- Claude Code >= 2.1.90 (algorithm salt: `friend-2026-401`)

## License

MIT
