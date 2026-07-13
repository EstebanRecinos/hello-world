"""Generate web/tokens.css from design/tokens.json (W3C Design Tokens).

Single source of truth: edit the JSON, never the CSS. Usage:
    python -m scripts.gen_tokens
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "design" / "tokens.json"
OUT = ROOT / "web" / "tokens.css"

HEADER = "/* GENERATED from design/tokens.json — do not edit by hand. */\n"


def color_vars(theme: dict) -> list[str]:
    return [f"  --{name}: {tok['$value']};" for name, tok in theme.items()]


def scalar_vars(prefix: str, group: dict) -> list[str]:
    out = []
    for name, tok in group.items():
        if name.startswith("$"):
            continue
        value = tok["$value"]
        if isinstance(value, list):  # fontFamily
            value = ", ".join(f'"{v}"' if " " in v else v for v in value)
        out.append(f"  --{prefix}-{name}: {value};")
    return out


def main() -> None:
    t = json.loads(TOKENS.read_text())
    light = color_vars(t["color"]["light"])
    dark = color_vars(t["color"]["dark"])
    scalars = (
        scalar_vars("space", t["space"])
        + scalar_vars("radius", t["radius"])
        + scalar_vars("size", t["size"])
        + scalar_vars("font", t["type"]["family"])
        + scalar_vars("text", t["type"]["scale"])
        + scalar_vars("motion", t["motion"])
    )
    css = "\n".join(
        [
            HEADER,
            ":root {", *light, *scalars, "}",
            "@media (prefers-color-scheme: dark) {", "  :root {", *["  " + l for l in dark], "  }", "}",
            ':root[data-theme="dark"] {', *dark, "}",
            ':root[data-theme="light"] {', *light, "}",
            "",
        ]
    )
    OUT.write_text(css)
    print(f"Wrote {OUT} ({len(css.splitlines())} lines)")


if __name__ == "__main__":
    main()
