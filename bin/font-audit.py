#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.53", "brotli>=1.1", "uharfbuzz>=0.39"]
# ///
"""Check the swashes font-features.py bakes in against the text it will actually shape.

font-features.py decides each rule from geometry, but it decides it one neighbour at a
time, from a font that has not been built yet. This shapes real words with the built font
and re-applies the same protrusion test to every glyph an arm passes over -- which is the
only way to catch the failures that come from the gap between the two:

  - an arm reaching further than its neighbour is wide, landing on the letter beyond
  - a lookahead letter that a later rule swapped for something taller
  - two arms arriving in the same letter from opposite sides

A clean run is the invariant; anything reported is a pair the rules believe is fine and
the shaper draws overlapping. Usage:

    bin/font-audit.py                    # audit the built subset
    bin/font-audit.py --font x.woff2     # audit some other build
    bin/font-audit.py --words 20000      # widen the sample
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import sys
from collections import Counter
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
WORDLIST = Path("/usr/share/dict/words")

# Reuse the generator's own geometry, so the audit cannot drift from the rules it checks.
_spec = importlib.util.spec_from_file_location("ff", ROOT / "bin/font-features.py")
ff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ff)


class Shaper:
    def __init__(self, path: Path):
        self.tt = TTFont(path)
        self.tt.flavor = None  # harfbuzz wants a plain sfnt, not woff/woff2
        buf = io.BytesIO()
        self.tt.save(buf)
        self.font = hb.Font(hb.Face(buf.getvalue()))
        self.order = self.tt.getGlyphOrder()
        self.geom = ff.Geometry(self.tt)

    def __call__(self, text: str) -> list[tuple[str, float]]:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {"kern": True, "liga": True, "calt": True})
        out, x = [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], x + pos.x_offset))
            x += pos.x_advance
        return out


def clashes(shaper: Shaper, run):
    """(protrusion, arm, victim, distance) for every overhang that fails its own test."""
    geom = shaper.geom
    out = []
    for idx, (name, x) in enumerate(run):
        if "." not in name:
            continue
        base = name.split(".")[0]
        if base not in geom.hmtx.metrics:
            continue
        base_l, base_r = geom.overhang(base)
        var_l, var_r = geom.overhang(name)
        for side, net in (("L", var_l - base_l), ("R", var_r - base_r)):
            # Only real arms, by the same gate the derivation uses -- a few units of
            # ordinary sidebearing is not something a neighbour has to clear.
            if net < ff.MIN_OVERHANG:
                continue
            ink = geom.overhang_ink(name, side, base)
            if not ink:
                continue
            # Same split the derivation makes: the innermost columns of an overhang hold
            # the letter's own terminal as well as the arm, so they answer "is there room"
            # but not "is this swallowing its neighbour".
            arm = geom.arm_ink(name, side, base)
            facing = geom.orientation(name, side, base)
            # Same two tests the derivation applies, in the same order: an arm needs a
            # short letter under it before the question of clearance is worth asking.
            ceiling = geom.x_top + ff.ARC_HEADROOM
            floor = geom.x_bottom - ff.ARC_HEADROOM
            for j, (other, ox) in enumerate(run):
                if j == idx or other == "space":
                    continue
                # Measure in the arm's own frame, which is the frame the derivation
                # used. Slicing on a shared absolute grid instead shifts the column
                # boundaries by up to half a column, and at the tip of a swash -- where
                # the outline is near vertical and a neighbour's stem is a couple of
                # units away -- that alone flips the verdict. The point here is to catch
                # what the rules failed to model, not to re-litigate their quantisation.
                cols = geom.columns(other, ox - x)
                worst = float("-inf")
                for k, (amin, amax) in ink.items():
                    span = cols.get(k)
                    if span is None:
                        continue
                    bmin, bmax = span
                    if facing > 0:
                        if k in arm and amin < bmin - ff.ENGULF_SLACK:
                            worst = float("inf")
                            break
                        if k in arm and bmax > ceiling:
                            worst = float("inf")
                            break
                        worst = max(worst, bmax - amax)
                    else:
                        if k in arm and amax > bmax + ff.ENGULF_SLACK:
                            worst = float("inf")
                            break
                        if k in arm and bmin < floor:
                            worst = float("inf")
                            break
                        worst = max(worst, amin - bmin)
                if worst != float("-inf") and worst > ff.PROTRUSION_LIMIT:
                    out.append((worst, name, other, abs(j - idx)))
    return out


def sample(limit: int) -> list[str]:
    if not WORDLIST.exists():
        sys.exit(f"no word list at {WORDLIST}; pass --text instead")
    words = [w.strip() for w in WORDLIST.read_text().splitlines()
             if w.strip().isalpha() and 3 <= len(w.strip()) <= 12]
    step = max(1, len(words) // limit)
    return words[::step]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", type=Path,
                    default=ROOT / "assets/fonts/SundayClub-Bold.subset.woff2")
    ap.add_argument("--words", type=int, default=5000, help="word list sample size")
    ap.add_argument("--text", nargs="*", help="audit these strings instead of the list")
    ap.add_argument("--top", type=int, default=15, help="offenders to print")
    ap.add_argument("--max", type=float, default=1.0, metavar="PCT",
                    help="exit non-zero above this %% of words (default 1.0)")
    args = ap.parse_args()

    shaper = Shaper(args.font)
    words = args.text if args.text else sample(args.words)

    bad, worst, by_distance = 0, {}, Counter()
    variants = glyphs = 0
    for w in words:
        run = shaper(w)
        glyphs += sum(1 for n, _ in run if n != "space")
        variants += sum(1 for n, _ in run if "." in n)
        found = clashes(shaper, run)
        if not found:
            continue
        bad += 1
        for p, arm, victim, dist in found:
            by_distance[dist] += 1
            key = (arm, victim, dist)
            if p > worst.get(key, (-1e9,))[0]:
                worst[key] = (p, w)

    print(f"{args.font.name}: {len(words)} words, "
          f"{variants}/{glyphs} glyphs decorated ({100 * variants / glyphs:.0f}%)")
    print(f"{bad} words ({100 * bad / len(words):.1f}%) contain an arm that fails the "
          f"fit test")
    if by_distance:
        print(f"failures by distance from the arm: {dict(sorted(by_distance.items()))}")
    for (arm, victim, dist) in sorted(worst, key=lambda k: -worst[k][0])[:args.top]:
        p, w = worst[(arm, victim, dist)]
        print(f"  protrusion {p:8.0f}  {arm:<12s} over {victim:<12s} "
              f"(gap {dist})  e.g. {w}")
    rate = 100 * bad / len(words)
    return 1 if rate > args.max else 0


if __name__ == "__main__":
    sys.exit(main())
