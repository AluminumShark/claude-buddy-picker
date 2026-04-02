"""ANSI-colored buddy card rendering."""

from buddy_picker.algorithm import STAT_NAMES

RARITY_ICON = {
    "common": "\u2605",
    "uncommon": "\u25c8",
    "rare": "\u2726",
    "epic": "\u2756",
    "legendary": "\u265b",
}

RARITY_COLOR = {
    "common": "37",
    "uncommon": "32",
    "rare": "34",
    "epic": "35",
    "legendary": "33",
}

SPECIES_EMOJI = {
    "duck": "\U0001f986", "goose": "\U0001fab3", "blob": "\U0001fae0",
    "cat": "\U0001f431", "dragon": "\U0001f409", "octopus": "\U0001f419",
    "owl": "\U0001f989", "penguin": "\U0001f427", "turtle": "\U0001f422",
    "snail": "\U0001f40c", "ghost": "\U0001f47b", "axolotl": "\U0001f98e",
    "capybara": "\U0001f9ab", "cactus": "\U0001f335", "robot": "\U0001f916",
    "rabbit": "\U0001f430", "mushroom": "\U0001f344", "chonk": "\U0001f408",
}

HAT_DISPLAY = {
    "none": "(none)",
    "crown": "\U0001f451 crown",
    "tophat": "\U0001f3a9 tophat",
    "propeller": "\U0001f9e2 propeller",
    "halo": "\U0001f607 halo",
    "wizard": "\U0001f9d9 wizard",
    "beanie": "\U0001f9f6 beanie",
    "tinyduck": "\U0001f986 tinyduck",
}


def _display_width(s: str) -> int:
    """Approximate terminal display width, accounting for wide/emoji chars."""
    w = 0
    for ch in s:
        cp = ord(ch)
        if cp > 0xFFFF or 0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x9FFF or \
           0xF900 <= cp <= 0xFAFF or 0xFE10 <= cp <= 0xFE6F or 0xFF01 <= cp <= 0xFF60 or \
           0x20000 <= cp <= 0x2FA1F:
            w += 2
        else:
            w += 1
    return w


def c(text: str, code: str) -> str:
    """Wrap *text* in an ANSI escape sequence."""
    return f"\033[{code}m{text}\033[0m"


def display_buddy(b: dict, uid: str = "", compact: bool = False) -> None:
    rc = RARITY_COLOR[b["rarity"]]
    icon = RARITY_ICON[b["rarity"]]
    emoji = SPECIES_EMOJI.get(b["species"], "?")

    if compact:
        shiny_tag = c(" SHINY", "1;33") if b["shiny"] else ""
        hat_tag = f" hat={b['hat']}" if b["hat"] != "none" else ""
        stats_str = " ".join(f"{k}:{v}" for k, v in b["stats"].items())
        print(f"  {c(icon + ' ' + b['rarity'].upper(), rc)} {emoji} {b['species']}"
              f" eye={b['eye']}{hat_tag}{shiny_tag}")
        print(f"    {stats_str}")
        if uid:
            print(f"    uid: {uid}")
        return

    print()
    print(c(f"  \u256d{'\u2500' * 40}\u256e", rc))
    title = f"{icon} {b['rarity'].upper()}"
    species_str = f"{emoji} {b['species'].upper()}"
    padding = 40 - _display_width(title) - _display_width(species_str) - 2
    print(c(f"  \u2502 {title}{' ' * max(padding, 1)}{species_str} \u2502", rc))

    if b["shiny"]:
        shiny_text = "SHINY"
        pad = (40 - len(shiny_text)) // 2
        print(c(f"  \u2502{' ' * pad}{shiny_text}{' ' * (40 - pad - len(shiny_text))}\u2502",
               "1;33"))

    hat_line = f"hat: {HAT_DISPLAY[b['hat']]}" if b["hat"] != "none" else ""
    eye_line = f"eye: {b['eye']}"
    info = f"{eye_line}  {hat_line}".strip()
    info_pad = 39 - _display_width(info)
    print(c(f"  \u2502 {info}{' ' * max(info_pad, 0)}\u2502", rc))

    print(c(f"  \u2502{'\u2500' * 40}\u2502", rc))
    for name in STAT_NAMES:
        val = b["stats"][name]
        filled = val // 5
        bar = "\u2588" * filled + "\u2591" * (20 - filled)
        print(c(f"  \u2502 {name:<10} {bar} {val:>3} \u2502", rc))

    print(c(f"  \u2570{'\u2500' * 40}\u256f", rc))
    if uid:
        print(f"    uid: {c(uid, '2')}")
    print()
