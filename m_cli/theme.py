"""`m theme`: build an oh-my-posh theme with plain characters and your colors.

Downloads one of the official oh-my-posh themes, swaps the icon / powerline
characters for plain ASCII (so prompts paste cleanly into agents and logs),
shortens the username, and on Windows recolors it with your accent color.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_THEME = "stelbent-compact.minimal"
THEME_URL = "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/{name}.omp.json"

# (old, new) pairs applied to the raw theme text. The old strings are the
# literal \uXXXX escapes as they appear inside the JSON file.
SWAPS = [
    ('"powerline_symbol": "\\ue0b0",', ""),
    ('"style": "powerline"', '"style": "plain"'),
    ("\\ueba9 ", "ssh "),
    ("\\uf42e", "ok"),
    ("\\ue0a0 ", ""),
    ("\\u250c ", ""),
    ("\\u2514", ""),
    ("\\u2502", "|"),
    ("\\u2191", "^"),
    ("\\u2193", "v"),
    ("\\u2262", ""),
    ("\\u2261", "="),
    ("\\u2713 ", "ok "),
    ("\\u25b7 ", "> "),
    ("\\u25f4 ", "m "),
    ("\\u2c62 ", "r "),
    ("\\u25b6 ", "> "),
]

# first word of the username, lowercased (the quotes are escaped for JSON)
USERNAME_FROM = "{{ .UserName }}"
USERNAME_TO = '{{ index (splitList \\" \\" .UserName) 0 | lower }}'

# stelbent colors that get replaced by the accent color
PATH_BG = "#91ddff"
TIME_FG = "#689f38"
TIME_BRIGHTEN = 0.4  # how far the time color moves toward white

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class ThemeError(Exception):
    pass


def theme_path() -> Path:
    override = os.environ.get("M_THEME_FILE")
    return Path(override) if override else Path.home() / "theme.omp.json"


def write_theme(path: Path, text: str) -> None:
    # Plain write (no temp file + rename) so a symlink, like the WSL one that
    # points at the Windows theme, keeps pointing where it did.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def fetch_theme(name: str) -> str:
    if name.endswith(".omp.json"):
        name = name[: -len(".omp.json")]
    if not _NAME_RE.match(name):
        raise ThemeError(f"'{name}' doesn't look like a theme name")
    url = THEME_URL.format(name=name)
    req = urllib.request.Request(url, headers={"User-Agent": "m-cli"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ThemeError(f"theme '{name}' not found, nothing changed. see https://ohmyposh.dev/docs/themes")
        raise ThemeError(f"couldn't download '{name}' (http {e.code}), nothing changed")
    except (urllib.error.URLError, OSError) as e:
        raise ThemeError(f"couldn't download '{name}': {e}")
    try:
        json.loads(text)
    except ValueError:
        raise ThemeError(f"'{name}' didn't download as valid json, nothing changed")
    return text


def apply_swaps(text: str) -> str:
    for old, new in SWAPS:
        text = text.replace(old, new)
    return text


def shorten_username(text: str) -> str:
    return text.replace(USERNAME_FROM, USERNAME_TO)


def abgr_to_hex(value: int) -> str:
    """Windows stores the accent color as 0xAABBGGRR."""
    return "#{:02x}{:02x}{:02x}".format(value & 255, (value >> 8) & 255, (value >> 16) & 255)


def windows_accent():
    """The accent color from Windows' personalization settings, or None."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as key:
            value, _ = winreg.QueryValueEx(key, "AccentColor")
    except (ImportError, OSError):
        return None
    return abgr_to_hex(int(value))


def brighten(hex_color: str, amount: float = TIME_BRIGHTEN) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * amount) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def apply_accent(text: str, accent: str) -> str:
    return text.replace(PATH_BG, accent).replace(TIME_FG, brighten(accent))


def build_theme(name: str, accent=None) -> str:
    text = fetch_theme(name)
    text = apply_swaps(text)
    text = shorten_username(text)
    if accent:
        text = apply_accent(text, accent)
    try:
        json.loads(text)
    except ValueError as e:
        raise ThemeError(f"the edited theme isn't valid json ({e}), nothing changed")
    return text


def parse_args(args):
    name, accent = DEFAULT_THEME, None
    i = 0
    seen_name = False
    while i < len(args):
        arg = args[i]
        if arg == "--accent":
            if i + 1 >= len(args):
                raise ThemeError("--accent needs a color, like --accent #0078d4")
            accent = args[i + 1]
            if not _HEX_RE.match(accent):
                raise ThemeError(f"'{accent}' isn't a hex color like #0078d4")
            i += 2
        elif arg.startswith("-"):
            raise ThemeError(f"unknown option {arg}")
        elif not seen_name:
            name, seen_name = arg, True
            i += 1
        else:
            raise ThemeError("usage: m theme [name] [--accent #hex]")
    return name, accent


def run(args) -> str:
    """Build the theme from cli args, write it, return a status message."""
    name, accent = parse_args(args)
    accent_note = "your --accent" if accent else None
    if accent is None:
        accent = windows_accent()
        accent_note = "Windows accent" if accent else None
    text = build_theme(name, accent)
    path = theme_path()
    write_theme(path, text)
    colors = f"{accent_note} {accent}" if accent else "the theme's own colors (no accent found, pass --accent #hex)"
    return f"theme '{name}' written to {path}\ncolors: {colors}"
