#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools>=4.53", "brotli>=1.1"]
# ///
"""Bake contextual alternate (calt) rules into SundayClub-Bold from glyph geometry.

Sunday Club exposes swsh/titl as *single* substitutions and salt with exactly one
alternate per glyph, so `font-feature-settings` can only ever be applied to a whole
element -- there is no way to say "swash just this f". Doing it by hand means wrapping
single letters in <span>s, which additionally breaks liga/dlig/calt shaping across the
element boundary.

So instead we put the decision in the font's own calt table, which browsers apply by
default with no markup at all. A decorative variant is used wherever its overhanging
ink clears the neighbouring letters; otherwise the plain glyph stands.

Whether a variant "fits" is derived from the outlines, not hand-authored: we measure
each variant's ink column by column and require a clear vertical gap against the
neighbour sitting in that same column.

Usage:
    bin/font-features.py --report        # derived rules, writes nothing
    bin/font-features.py --fea           # write the .fea only
    bin/font-features.py                 # full build (fea + subset woff2/woff + b64)
"""

from __future__ import annotations

import argparse
import base64
import io
import sys
import unicodedata
from collections import OrderedDict, defaultdict
from pathlib import Path

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.basePen import BasePen
from fontTools.otlLib.builder import buildLookup, buildPairPosGlyphsSubtable, buildValue
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent

# Pristine vendor file, never written to.
SOURCE = ROOT / "assets/fonts/SundayClub-Bold.woff"
# Derived artefacts, already referenced by _includes/styles/inline-fonts.scss.
OUT_WOFF2 = ROOT / "assets/fonts/SundayClub-Bold.subset.woff2"
OUT_WOFF = ROOT / "assets/fonts/SundayClub-Bold.subset.woff"
OUT_B64 = ROOT / "_includes/fonts/SundayClub-Bold.woff2.b64"
OUT_FEA = ROOT / "bin/sundayclub.fea"

# Unicode coverage of the shipped subset. Stated explicitly rather than read back
# from the previous subset file, so a build can never feed on its own output.
SUBSET_RANGES = (
    "0x20-0x7e,0xa1-0xa9,0xab,0xae-0xb1,0xb4,0xb6-0xb8,0xbb,0xbd,0xbf-0xff,"
    "0x131,0x152-0x153,0x2c6,0x2da,0x2dc,0x2013-0x2014,0x2018-0x201a,0x201c-0x201e,"
    "0x2020-0x2022,0x2026,0x2030,0x2039-0x203a,0x2044,0x20ac,0x2212,0xfb00-0xfb04"
)


def subset_unicodes() -> set[int]:
    out: set[int] = set()
    for part in SUBSET_RANGES.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return out


# --- tuning -----------------------------------------------------------------

# Features whose glyphs are candidates for automatic use, most decorative first.
# Ties in overhang are broken by this order.
FEATURE_PRIORITY = ["swsh", "titl", "salt", "ss04", "ss03", "ss02", "ss01"]

# Ink this far outside the advance box counts as an overhang needing cover (units/em=1000).
MIN_OVERHANG = 40
# A swash may dip this far below a neighbour's own lower edge before we treat it as
# engulfing the letter rather than arcing past it.
ENGULF_SLACK = 50
# How far a neighbour must stay *inside* the swash's silhouette, in font units.
#
# Raw clearance is the wrong measure here: Sunday Club's swashes are drawn to arc
# over their neighbours and graze them, so good pairs interpenetrate freely (o before
# f.swsh overlaps by 186 units and is exactly what you'd hand-pick) while bad pairs
# overlap less (l before f.swsh, 174). What actually distinguishes them is whether the
# neighbour pokes out past the swash -- an ascender or a dot piercing the stroke reads
# as a mistake, a short letter tucked beneath it reads as intentional.
PROTRUSION_LIMIT = -20
# Width of the vertical slices used for the fit test. Small enough that the
# quantisation error at a glyph boundary stays under half a percent of the em.
COLUMN = 4

# Variants never applied automatically (still reachable via the .salt/.swsh/.titl
# CSS classes). Sunday Club's ss01-ss04 are stylistic preferences rather than
# contextual fixes, so they stay opt-in.
EXCLUDE_VARIANTS: set[str] = set()
EXCLUDE_FEATURES = {"ss01", "ss02", "ss03", "ss04"}
EXCLUDE_BASES: set[str] = set()

# Which letters may be swashed automatically.
#
# calt matches positions, it cannot count, so there is no way to say "at most two
# swashes per word" -- every eligible position fires. Left unrestricted that turns
# ordinary words into a thicket. Density is therefore controlled by which letters opt
# in: capitals are naturally sparse (roughly one per word) and are the classic place
# for a swash, plus the lowercase letters whose extenders are this face's signature.
# Pass --all-letters to lift the restriction and see the maximal version.
AUTO_BASES: set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") | {
    "f", "g", "j", "k", "t", "x", "y", "z", "ampersand",
}

# Whether a word's first letter may take a left swash, sweeping back into the word gap.
# The space before it is widened to compensate (see add_word_space_kerns), so word
# spacing survives. Set False to require a real letter before every left swash.
ALLOW_WORD_INITIAL = True
# ...but only for swashes with a short reach. A capital's arm (H.swsh reaches 176) reads
# as part of the letterform, whereas a long lowercase arc (t.swsh reaches 340) drawn over
# an empty gap reads as a stray mark floating in front of the word -- it needs a letter
# to arc over. Capitals clear this bar, the big lowercase sweeps do not.
WORD_INITIAL_MAX_REACH = 200


# --- geometry ---------------------------------------------------------------


class ColumnPen(BasePen):
    """Collect the vertical extent of a glyph's ink in fixed-width vertical slices.

    A per-column envelope is the right test here: it treats a letter as a solid
    silhouette, so a swash cannot be judged "clear" by threading through a counter.
    """

    def __init__(self, glyph_set, xoff=0.0, column=COLUMN):
        super().__init__(glyph_set)
        self.xoff = xoff
        self.column = column
        self.cols: dict[int, list[float]] = {}
        self._cur = None
        self._start = None

    def _point(self, x, y):
        k = int((x + self.xoff) // self.column)
        span = self.cols.get(k)
        if span is None:
            self.cols[k] = [y, y]
        else:
            if y < span[0]:
                span[0] = y
            if y > span[1]:
                span[1] = y

    def _segment(self, p0, p1):
        (x0, y0), (x1, y1) = p0, p1
        steps = max(2, int(max(abs(x1 - x0), abs(y1 - y0)) / (self.column / 2)) + 1)
        for i in range(steps + 1):
            t = i / steps
            self._point(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    def _moveTo(self, pt):
        self._cur = self._start = pt
        self._point(*pt)

    def _lineTo(self, pt):
        self._segment(self._cur, pt)
        self._cur = pt

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur
        prev = p0
        for i in range(1, 25):
            t = i / 24
            u = 1 - t
            x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
            y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
            self._segment(prev, (x, y))
            prev = (x, y)
        self._cur = p3

    def _closePath(self):
        if self._cur and self._start and self._cur != self._start:
            self._segment(self._cur, self._start)
        self._cur = self._start


class Kerning:
    """Flattened GPOS pair kerning, both explicit pairs and class pairs."""

    def __init__(self, font: TTFont):
        self.pairs: dict[tuple[str, str], int] = {}
        self.classes: list[tuple[dict, dict, list, set]] = []
        if "GPOS" not in font:
            return
        for lookup in font["GPOS"].table.LookupList.Lookup:
            if lookup.LookupType != 2:
                continue
            for st in lookup.SubTable:
                if st.Format == 1:
                    for first, pairset in zip(st.Coverage.glyphs, st.PairSet):
                        for rec in pairset.PairValueRecord:
                            v = getattr(rec.Value1, "XAdvance", 0) or 0
                            if v:
                                self.pairs[(first, rec.SecondGlyph)] = v
                elif st.Format == 2:
                    self.classes.append(
                        (st.ClassDef1.classDefs, st.ClassDef2.classDefs,
                         st.Class1Record, set(st.Coverage.glyphs))
                    )

    def __call__(self, left: str, right: str) -> int:
        hit = self.pairs.get((left, right))
        if hit is not None:
            return hit
        for cd1, cd2, recs, cov in self.classes:
            if left not in cov:
                continue
            c1, c2 = cd1.get(left, 0), cd2.get(right, 0)
            try:
                v = getattr(recs[c1].Class2Record[c2].Value1, "XAdvance", 0) or 0
            except (IndexError, AttributeError):
                v = 0
            if v:
                return v
        return 0


class Geometry:
    """Glyph measurements, memoised by (glyph, x offset)."""

    def __init__(self, font: TTFont):
        self.font = font
        self.glyph_set = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self.kern = Kerning(font)
        self.xheight = getattr(font["OS/2"], "sxHeight", 500) or 500
        self._cache: dict[tuple[str, int], dict[int, list[float]]] = {}

    def advance(self, name: str) -> int:
        return self.hmtx[name][0]

    def columns(self, name: str, xoff: float = 0.0) -> dict[int, list[float]]:
        key = (name, int(round(xoff)))
        hit = self._cache.get(key)
        if hit is None:
            pen = ColumnPen(self.glyph_set, xoff=xoff)
            self.glyph_set[name].draw(pen)
            hit = self._cache[key] = pen.cols
        return hit

    def overhang(self, name: str) -> tuple[float, float]:
        """Ink extending left of the origin and right of the advance."""
        cols = self.columns(name)
        if not cols:
            return 0.0, 0.0
        adv = self.advance(name)
        xs = [k * COLUMN for k in cols]
        left = max(0.0, -min(xs))
        right = max(0.0, (max(xs) + COLUMN) - adv)
        return left, right

    def overhang_ink(self, name: str, side: str,
                     base: str | None = None) -> dict[int, list[float]]:
        """Only the ink the variant adds beyond the plain glyph it replaces.

        Measuring from the advance box alone is not enough: plain `f` already pokes
        9 units left of its origin, and that sliver of ordinary sidebearing sits low
        enough to look like a collision with whatever precedes it -- which wrongly
        disqualified `o` before `f.swsh`, the very pairing in "Hofer". The swash is
        the ink the variant adds, so the plain glyph's own overhang is the baseline.
        """
        cols = self.columns(name)
        pad_l, pad_r = self.overhang(base) if base else (0.0, 0.0)
        if side == "L":
            return {k: v for k, v in cols.items() if (k + 1) * COLUMN <= -pad_l}
        edge = self.advance(name) + pad_r
        return {k: v for k, v in cols.items() if k * COLUMN >= edge}

    def orientation(self, name: str, side: str, base: str | None = None) -> int:
        """+1 if the overhang arcs over its neighbours, -1 if it sweeps beneath them."""
        ink = self.overhang_ink(name, side, base)
        if not ink:
            return 1
        # Median of the per-column midpoints, not of the whole bounding box: a swash
        # that arcs overhead still dips to the baseline where it rejoins the stem, and
        # that one low column is enough to drag a min/max midpoint the wrong side of
        # the line.
        mids = sorted((lo + hi) / 2 for lo, hi in ink.values())
        mid = mids[len(mids) // 2]
        return 1 if mid >= self.xheight / 2 else -1

    def protrusion(self, variant: str, neighbour: str, side: str,
                   base: str | None = None) -> float:
        """How far a neighbour escapes the overhang's silhouette.

        Negative means the neighbour stays tucked inside; positive means it pokes
        out past the swash. Returns -inf when the two never share a column.
        """
        ink = self.overhang_ink(variant, side, base)
        if not ink:
            return float("-inf")
        if side == "R":
            offset = self.advance(variant) + self.kern(variant, neighbour)
        else:
            offset = -(self.advance(neighbour) + self.kern(neighbour, variant))
        cols = self.columns(neighbour, offset)
        facing = self.orientation(variant, side, base)
        worst = float("-inf")
        for k, (amin, amax) in ink.items():
            span = cols.get(k)
            if span is None:
                continue
            bmin, bmax = span
            if facing > 0:
                # Swash on top: the neighbour must not rise past it, and the swash
                # must not dive underneath the neighbour and swallow it whole.
                if amin < bmin - ENGULF_SLACK:
                    return float("inf")
                worst = max(worst, bmax - amax)
            else:
                if amax > bmax + ENGULF_SLACK:
                    return float("inf")
                worst = max(worst, amin - bmin)
        return worst

    def tucks(self, variant: str, neighbour: str, side: str,
              base: str | None = None) -> bool:
        return self.protrusion(variant, neighbour, side, base) <= PROTRUSION_LIMIT


def min_gap(a: dict[int, list[float]], b: dict[int, list[float]]) -> float:
    """Smallest vertical gap between two ink maps in any column they share.

    Positive means they pass over/under each other cleanly; negative means the
    outlines interpenetrate by that much.
    """
    worst = float("inf")
    for k, (amin, amax) in a.items():
        span = b.get(k)
        if span is None:
            continue
        bmin, bmax = span
        worst = min(worst, max(bmin - amax, amin - bmax))
    return worst


# --- reading the existing feature tables ------------------------------------


class Lookup:
    """A GSUB lookup flattened into something we can re-emit as .fea."""

    def __init__(self, index: int):
        self.index = index
        self.singles: OrderedDict[str, str] = OrderedDict()
        self.alternates: OrderedDict[str, list[str]] = OrderedDict()
        self.ligatures: list[tuple[list[str], str]] = []
        self.contextual: list[tuple[list[list[str]], str, list[list[str]], str]] = []

    @property
    def name(self) -> str:
        return f"lk{self.index:02d}"

    def is_empty(self) -> bool:
        return not (self.singles or self.alternates or self.ligatures or self.contextual)


def read_lookup(lookups, index: int) -> Lookup:
    src = lookups[index]
    out = Lookup(index)
    for st in src.SubTable:
        if getattr(st, "mapping", None) is not None:
            out.singles.update(st.mapping)
        elif getattr(st, "alternates", None) is not None:
            out.alternates.update(st.alternates)
        elif getattr(st, "ligatures", None) is not None:
            for first, ligs in st.ligatures.items():
                for lig in ligs:
                    out.ligatures.append(([first] + list(lig.Component), lig.LigGlyph))
        elif st.__class__.__name__ == "ChainContextSubst" and st.Format == 3:
            back = [sorted(c.glyphs) for c in st.BacktrackCoverage]
            ahead = [sorted(c.glyphs) for c in st.LookAheadCoverage]
            inputs = [sorted(c.glyphs) for c in st.InputCoverage]
            if len(inputs) != 1 or len(st.SubstLookupRecord) != 1:
                raise SystemExit(
                    f"lookup {index}: chain context shape not supported by this script"
                )
            target = lookups[st.SubstLookupRecord[0].LookupListIndex]
            mapping = {}
            for s2 in target.SubTable:
                mapping.update(getattr(s2, "mapping", {}) or {})
            for g in inputs[0]:
                if g in mapping:
                    out.contextual.append((back, g, ahead, mapping[g]))
        else:
            raise SystemExit(
                f"lookup {index}: unsupported subtable {st.__class__.__name__}"
            )
    return out


def read_features(font: TTFont) -> OrderedDict[str, list[Lookup]]:
    gsub = font["GSUB"].table
    lookups = gsub.LookupList.Lookup
    out: OrderedDict[str, list[Lookup]] = OrderedDict()
    for rec in gsub.FeatureList.FeatureRecord:
        if rec.FeatureTag in out:
            continue  # same feature repeated per script; lookups are shared
        out[rec.FeatureTag] = [read_lookup(lookups, i) for i in rec.Feature.LookupListIndex]
    return out


def variant_map(features) -> dict[str, dict[str, str]]:
    """base glyph -> {feature tag: variant glyph}, for substitution features only."""
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for tag, lookups in features.items():
        if tag in ("liga", "dlig", "calt"):
            continue
        for lk in lookups:
            for base, var in lk.singles.items():
                out[base][tag] = var
            for base, alts in lk.alternates.items():
                out[base][tag] = alts[0]
    return out


# --- rule derivation ---------------------------------------------------------


class Rule:
    def __init__(self, base, variant, feature, over_l, over_r, left, right):
        self.base = base
        self.variant = variant
        self.feature = feature
        self.over_l = over_l
        self.over_r = over_r
        self.left = left          # allowed preceding glyphs (None = unconstrained)
        self.right = right        # allowed following glyphs (None = unconstrained)

    @property
    def weight(self):
        return self.over_l + self.over_r


def neighbour_glyphs(font: TTFont) -> list[str]:
    """Plain letters a word can realistically put next to a swash.

    Restricted to the shipped subset's coverage: naming a glyph in a calt class keeps
    it alive through layout closure, so reaching outside the subset would drag the
    whole Latin Extended range back into an inlined, base64'd critical asset.
    """
    keep = subset_unicodes()
    out = []
    for cp, name in font["cmap"].getBestCmap().items():
        if cp not in keep:
            continue
        if unicodedata.category(chr(cp)).startswith("L") and "." not in name:
            out.append(name)
    return sorted(set(out))


def derive_rules(geom: Geometry, variants, neighbours) -> list[Rule]:
    rules: list[Rule] = []
    for base in sorted(variants):
        if base in EXCLUDE_BASES:
            continue
        if AUTO_BASES and base not in AUTO_BASES:
            continue
        candidates = []
        for tag, var in variants[base].items():
            if tag in EXCLUDE_FEATURES or var in EXCLUDE_VARIANTS:
                continue
            over_l, over_r = geom.overhang(var)
            base_l, base_r = geom.overhang(base)
            over_l, over_r = over_l - base_l, over_r - base_r
            if max(over_l, over_r) < MIN_OVERHANG:
                # No overhang means this is a style preference, not a contextual
                # fix -- applying it everywhere would just restyle the font.
                continue
            candidates.append((tag, var, over_l, over_r))

        # Most decorative first, so it wins the first-match race inside calt.
        candidates.sort(
            key=lambda c: (-(c[2] + c[3]), FEATURE_PRIORITY.index(c[0]))
        )

        for tag, var, over_l, over_r in candidates:
            left = right = None

            if over_l >= MIN_OVERHANG:
                left = [n for n in neighbours if geom.tucks(var, n, "L", base)]
                if not left:
                    continue
                # Word-initial needs a short reach *and* an overhead arc. A descender
                # sweep (j.titl) drawn under an empty gap bridges the two words at the
                # baseline, the same stray mark as a long arc drawn over one.
                if (ALLOW_WORD_INITIAL
                        and over_l <= WORD_INITIAL_MAX_REACH
                        and geom.orientation(var, "L", base) > 0):
                    left = ["space"] + left

            if over_r >= MIN_OVERHANG:
                right = [n for n in neighbours if geom.tucks(var, n, "R", base)]
                if not right:
                    continue

            rules.append(Rule(base, var, tag, over_l, over_r, left, right))

    rules.sort(key=lambda r: (-r.weight, r.base))
    return rules


# --- .fea emission -----------------------------------------------------------


def fmt_class(glyphs) -> str:
    return "[" + " ".join(glyphs) + "]"


def render_fea(features, rules, vendor_calt) -> str:
    out = io.StringIO()
    w = out.write
    w("# Generated by bin/font-features.py -- do not edit by hand.\n")
    w("# Re-run the script to regenerate, or compile a hand-edited copy with --fea-in.\n\n")

    # Reproduce every non-calt lookup exactly as it exists in the vendor font, so
    # rebuilding GSUB from this file is lossless.
    emitted: list[tuple[str, list[str]]] = []
    for tag, lookups in features.items():
        if tag == "calt":
            continue
        names = []
        for lk in lookups:
            if lk.is_empty():
                continue
            names.append(lk.name)
            w(f"lookup {lk.name} {{\n")
            for base, var in lk.singles.items():
                w(f"    sub {base} by {var};\n")
            for base, alts in lk.alternates.items():
                w(f"    sub {base} from {fmt_class(alts)};\n")
            for comps, lig in lk.ligatures:
                w(f"    sub {' '.join(comps)} by {lig};\n")
            w(f"}} {lk.name};\n\n")
        emitted.append((tag, names))

    for tag, names in emitted:
        w(f"feature {tag} {{\n")
        for n in names:
            w(f"    lookup {n};\n")
        w(f"}} {tag};\n\n")

    # calt: our derived rules first (most decorative wins), vendor's defensive
    # rules last so they act as a fallback when nothing fancier fits.
    w("feature calt {\n")
    for r in rules:
        parts = []
        if r.left is not None:
            parts.append(fmt_class(r.left))
        parts.append(f"{r.base}'")
        if r.right is not None:
            parts.append(fmt_class(r.right))
        w(f"    # {r.base} -> {r.variant} ({r.feature}, overhang L{r.over_l:.0f} R{r.over_r:.0f})\n")
        w(f"    sub {' '.join(parts)} by {r.variant};\n")
    if vendor_calt:
        w("\n    # Vendor rules, kept as a fallback for pairs that collide.\n")
        for back, g, ahead, sub in vendor_calt:
            parts = [fmt_class(c) for c in back] + [f"{g}'"] + [fmt_class(c) for c in ahead]
            w(f"    sub {' '.join(parts)} by {sub};\n")
    w("} calt;\n")
    return out.getvalue()


# --- build -------------------------------------------------------------------


def add_word_space_kerns(font: TTFont, rules: list[Rule]) -> int:
    """Widen the word space before a word-initial swash by exactly what it consumes.

    A left swash on a word's first letter sweeps back into the gap, so "Software
    Engineer" closes up into "SoftwareEngineer". Dropping the swash is one answer;
    making room for it is the better one. Each variant gets a (space, variant) kern
    equal to the ink it reaches back over, which restores the apparent gap.

    Appended as a new lookup on the existing kern feature rather than rebuilt from a
    .fea, so the vendor's 1975 pair kerns and its class-kerning compaction survive.
    """
    pairs = {}
    for r in rules:
        if not r.left or "space" not in r.left or r.over_l <= 0:
            continue
        pairs[("space", r.variant)] = (buildValue({"XAdvance": int(round(r.over_l))}), None)
    if not pairs or "GPOS" not in font:
        return 0

    gpos = font["GPOS"].table
    glyph_map = {g: i for i, g in enumerate(font.getGlyphOrder())}
    lookup = buildLookup([buildPairPosGlyphsSubtable(pairs, glyph_map)])
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    index = gpos.LookupList.LookupCount - 1
    for rec in gpos.FeatureList.FeatureRecord:
        if rec.FeatureTag == "kern":
            rec.Feature.LookupListIndex.append(index)
            rec.Feature.LookupCount = len(rec.Feature.LookupListIndex)
    return len(pairs)


def subset_to_coverage(font: TTFont) -> TTFont:
    """Subset to SUBSET_RANGES, keeping every layout feature intact."""
    unicodes = subset_unicodes()
    opts = Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True
    sub = Subsetter(options=opts)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    return font


def report(rules, geom):
    print(f"{'base':>6}  {'variant':<16}{'feat':<6}{'overL':>7}{'overR':>7}"
          f"{'left':>7}{'right':>7}  needs")
    for r in rules:
        needs = []
        if r.left is not None:
            needs.append("left")
        if r.right is not None:
            needs.append("right")
        print(f"{r.base:>6}  {r.variant:<16}{r.feature:<6}{r.over_l:>7.0f}{r.over_r:>7.0f}"
              f"{len(r.left) if r.left else 0:>7}{len(r.right) if r.right else 0:>7}"
              f"  {'+'.join(needs)}")
    print(f"\n{len(rules)} contextual rules")


def main() -> int:
    global PROTRUSION_LIMIT, AUTO_BASES
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="print derived rules, write nothing")
    ap.add_argument("--debug", metavar="VARIANT",
                    help="show per-neighbour gaps for one variant glyph, e.g. f.swsh")
    ap.add_argument("--all-letters", action="store_true",
                    help="let every letter be swashed, not just AUTO_BASES")
    ap.add_argument("--protrusion", type=float, default=PROTRUSION_LIMIT,
                    help=f"max protrusion past the swash, font units "
                         f"(default {PROTRUSION_LIMIT}; lower is stricter)")
    ap.add_argument("--fea", action="store_true", help="write the .fea and stop")
    ap.add_argument("--fea-in", type=Path, help="compile this .fea instead of generating one")
    args = ap.parse_args()
    PROTRUSION_LIMIT = args.protrusion
    if args.all_letters:
        AUTO_BASES = set()

    # recalcTimestamp=False keeps head.modified at the vendor font's value, so
    # rebuilding without changing anything produces byte-identical output.
    font = TTFont(SOURCE, recalcTimestamp=False)
    geom = Geometry(font)
    features = read_features(font)
    variants = variant_map(features)
    neighbours = neighbour_glyphs(font)
    vendor_calt = [c for lk in features.get("calt", []) for c in lk.contextual]

    if args.debug:
        dbase = args.debug.split(".")[0]
        adv = geom.advance(args.debug)
        ol, orr = geom.overhang(args.debug)
        print(f"{args.debug}: advance={adv} overhang L={ol:.0f} R={orr:.0f}")
        for side, over in (("L", ol), ("R", orr)):
            if over < MIN_OVERHANG:
                continue
            facing = ("arcs over" if geom.orientation(args.debug, side, dbase) > 0
                      else "sweeps under")
            print(f"  --- {side} side ({facing}), sorted by protrusion ---")
            scored = sorted((geom.protrusion(args.debug, n, side, dbase), n)
                            for n in neighbours)
            for g, n in scored:
                mark = "ok " if g <= PROTRUSION_LIMIT else "   "
                print(f"    {mark}{n:12s} {g:9.1f}")
        return 0

    rules = derive_rules(geom, variants, neighbours)

    if args.report:
        report(rules, geom)
        return 0

    if args.fea_in:
        fea = args.fea_in.read_text()
    else:
        fea = render_fea(features, rules, vendor_calt)
        OUT_FEA.write_text(fea)
        print(f"wrote {OUT_FEA.relative_to(ROOT)}  ({len(rules)} contextual rules)")
        if args.fea:
            return 0

    addOpenTypeFeaturesFromString(font, fea, tables=["GSUB"])
    tags = sorted({r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord})
    print(f"rebuilt GSUB, features: {' '.join(tags)}")

    added = add_word_space_kerns(font, rules)
    if added:
        print(f"added {added} word-space kerns for word-initial swashes")

    subset_to_coverage(font)

    font.flavor = "woff2"
    font.save(OUT_WOFF2)
    font.flavor = "woff"
    font.save(OUT_WOFF)
    OUT_B64.write_text(base64.b64encode(OUT_WOFF2.read_bytes()).decode())
    # maxp only settles once the font has been compiled out, so report from disk.
    print(f"subset to {TTFont(OUT_WOFF2)['maxp'].numGlyphs} glyphs")

    for p in (OUT_WOFF2, OUT_WOFF, OUT_B64):
        print(f"wrote {p.relative_to(ROOT)}  ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
