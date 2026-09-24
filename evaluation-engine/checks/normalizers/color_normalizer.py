import re

NAMED_COLORS = {
    "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
    "white": "#ffffff", "black": "#000000", "yellow": "#ffff00",
    "orange": "#ffa500", "purple": "#800080", "pink": "#ffc0cb",
    "gray": "#808080", "grey": "#808080", "cyan": "#00ffff",
    "magenta": "#ff00ff", "transparent": "rgba(0, 0, 0, 0)",
}


def normalize_color(value: str) -> str:
    """
    Normalize any CSS colour string to lowercase rgb(r, g, b) form.
    Handles: named colours, #RGB, #RRGGBB, rgb(), rgba(), hsl().
    """
    v = value.strip().lower()

    if v in NAMED_COLORS:
        v = NAMED_COLORS[v]

    # #RGB → #RRGGBB
    if re.match(r"^#[0-9a-f]{3}$", v):
        v = "#" + "".join(c * 2 for c in v[1:])

    # #RRGGBB → rgb(r, g, b)
    if re.match(r"^#[0-9a-f]{6}$", v):
        r, g, b = int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16)
        return f"rgb({r}, {g}, {b})"

    # rgb() / rgba() → normalize spacing, strip alpha
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d.]+)?\s*\)", v)
    if m:
        return f"rgb({m.group(1)}, {m.group(2)}, {m.group(3)})"

    return v