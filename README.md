# Claude Buddy Picker

Re-roll your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) `/buddy` companion pet by finding a `userID` that produces your desired attributes.

## How It Works

Claude Code generates your `/buddy` pet deterministically:

```
FNV-1a(userID + "friend-2026-401") -> Mulberry32 PRNG -> weighted rolls
```

Same `userID` always produces the same pet. This tool brute-force searches for a `userID` that yields your target combination, then writes it to `~/.claude.json`.

## Installation

```bash
git clone https://github.com/AluminumShark/claude-buddy-picker.git
cd claude-buddy-picker
uv sync
```

## Usage

```bash
# Interactive mode - pick attributes step by step
buddy-picker

# Hierarchical drill-down
buddy-picker --hierarchical

# Direct CLI search (filters can be combined)
buddy-picker --species dragon --rarity legendary --shiny

# Show your current buddy
buddy-picker --check

# Auto-apply the first result
buddy-picker --species cat --rarity epic --apply 1

# Restore original userID
buddy-picker --restore
```

After applying, **restart Claude Code** and run `/buddy` to see your new pet.

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

### Hats (8, uniform - common always gets "none")

`none` `crown` `tophat` `propeller` `halo` `wizard` `beanie` `tinyduck`

### Shiny

1% chance. Purely cosmetic bragging rights.

### Stats

5 stats: **DEBUGGING**, **PATIENCE**, **CHAOS**, **WISDOM**, **SNARK**

Each buddy gets one peak stat (boosted) and one dump stat (reduced). Higher rarity = higher base values.

## CLI Options

```
--species NAME       Filter by species
--rarity NAME        Minimum rarity (common/uncommon/rare/epic/legendary)
--eye CHAR           Eye style
--hat NAME           Hat type (none/crown/tophat/propeller/halo/wizard/beanie/tinyduck)
--shiny              Require shiny (1% base chance)
--min-stats N        Require ALL stats >= N
--count N            Number of results to find (default: 5)
--max N              Max search iterations (default: 50,000,000)
--apply N            Auto-apply the Nth result
--check              Show current buddy from ~/.claude.json
--restore            Restore original userID from backup
--hierarchical       Step-by-step attribute selection
```

## Development

```bash
git clone https://github.com/AluminumShark/claude-buddy-picker.git
cd claude-buddy-picker
uv sync --dev
uv run pytest -v
```

## Compatibility

- Python >= 3.10
- Windows, macOS, Linux
- Claude Code >= 2.1.90 (cli.js algorithm version `friend-2026-401`)

## License

MIT
