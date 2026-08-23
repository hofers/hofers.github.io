#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.53", "brotli>=1.1"]
# ///
"""Prune the inlined Source Sans Pro Light and regenerate its base64.

The vendor build carries a GPOS table three times the size of its outlines: 42.6KB
against 14.1KB of glyf, holding the `size` feature (an optical-size record no browser
consults) and kern pairs for glyphs the subset does not contain. Since this font is
inlined into the critical CSS of every page, that dead table is paid on every page
view, so it is worth pruning even though the charset is already minimal.

Kerning is kept -- it is only 4.8KB once pruned to the shipped glyphs, and body copy
is where it shows. Hinting (fpgm/prep/cvt) is kept too: 1.9KB for legibility at the
site's 20px base size on Windows.

Source of truth is the pristine vendor file, never the previous output -- subsetting
an already-subset font would silently ratchet the coverage down on every run.

Usage:
    bin/subset-sourcesans.py            # rebuild
    bin/subset-sourcesans.py --report   # measure, write nothing
"""

import base64
import io
import sys
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "assets/fonts/SourceSansPro-Light.vendor.woff2"
OUT_B64 = ROOT / "_includes/fonts/SourceSansPro-Light.woff2.b64"

# Everything the vendor file covers. Stated explicitly so a build can never quietly
# drop a glyph, and so the diff shows up here rather than in a binary.
COVERAGE = (
    "".join(chr(c) for c in range(0x20, 0x7F))  # basic latin
    + "‒–—―"                # figure dash, en, em, horizontal bar
    + "‘’“”"                # curly quotes
)

# 'size' is an optical-size record browsers ignore; 'frac' is unreachable without
# markup that asks for it. Neither is worth the table weight.
KEEP_FEATURES = ["kern", "ccmp", "liga", "clig"]


def build() -> bytes:
    font = TTFont(VENDOR)
    opts = Options()
    opts.layout_features = KEEP_FEATURES
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.drop_tables += ["FFTM"]
    sub = Subsetter(options=opts)
    sub.populate(text=COVERAGE)
    sub.subset(font)

    # Without this fontTools stamps head.modified on save, so an unchanged rebuild
    # still churns the 12KB base64 blob in git.
    font.recalcTimestamp = False

    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def describe(label: str, data: bytes) -> set[int]:
    font = TTFont(io.BytesIO(data))
    tables = {t: len(font.getTableData(t)) for t in font.keys() if t != "GlyphOrder"}
    print(
        f"{label:<10}{len(data):>7} bytes  {len(font.getGlyphOrder()):>4} glyphs  "
        f"GPOS={tables.get('GPOS', 0):>6}  glyf={tables.get('glyf', 0):>6}"
    )
    return set(font.getBestCmap())


def main() -> int:
    report_only = "--report" in sys.argv
    vendor = VENDOR.read_bytes()
    before = describe("vendor", vendor)
    data = build()
    after = describe("subset", data)

    lost = sorted(before - after)
    if lost:
        print("ERROR: coverage regressed: " + ", ".join(f"U+{c:04X}" for c in lost))
        return 1
    print(f"coverage unchanged ({len(after)} codepoints), "
          f"saved {len(vendor) - len(data)} bytes ({1 - len(data) / len(vendor):.0%})")

    if report_only:
        print("--report: nothing written")
        return 0

    OUT_B64.write_text(base64.b64encode(data).decode())
    print(f"wrote {OUT_B64.relative_to(ROOT)}  ({OUT_B64.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
