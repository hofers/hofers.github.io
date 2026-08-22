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

Variants whose flourish stays inside the advance box have no neighbour to clear, so
geometry cannot place them. Those (MIN_FLOURISH -- a tail below the baseline, or a sweep
into a widened advance) go word-final, where a flourish reads as terminal and fires at most
once per word; variants that are simply the letterform this face wants, differing only in
their interior where a silhouette test cannot see them at all, are named in ALWAYS_VARIANTS
and substituted unconditionally.

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

# Tie-break order when two variants of a letter overhang by the same amount, most
# decorative first. This is only a sort key -- it must name every substitution feature
# in the font, including the ones EXCLUDE_FEATURES turns off, or lifting an exclusion
# to experiment would raise ValueError in the sort below. Inclusion is decided by
# EXCLUDE_FEATURES/EXCLUDE_VARIANTS, not by membership here.
FEATURE_PRIORITY = ["swsh", "titl", "salt", "ss04", "ss03", "ss02", "ss01"]

# Width of the vertical slices used for the fit test. Small enough that the
# quantisation error at a glyph boundary stays under half a percent of the em.
COLUMN = 4

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
# How far an arm may reach past the far edge of the letter it arcs over.
#
# Geometry.covers requires an arm to stay inside its neighbour's advance, which is what
# makes a one-position test sound. Demanding that to the unit is too literal: f.swsh
# reaches 355 and the e after it is 352 wide, so "Hofer" lost the swash by three units of
# font -- a third of a printed pixel. One column is the right size for the allowance,
# because one column is the resolution the envelope is measured at: asking for containment
# to any finer than that is asking for precision the measurement does not have. Anything
# looser stops being rounding error and becomes the failure covers exists to prevent --
# at 40 units an arm reaches far enough past its neighbour to land on the ascender of the
# letter after it, which is where most of this script's collisions used to come from.
COVER_SLACK = COLUMN
# How much ink beyond the advance box is the letter's own terminal rather than an arm.
#
# The overhang test cuts at the advance, and a variant drawn narrower than the letter it
# replaces pushes its own body a few units past that cut: Z.swsh keeps plain Z's top bar
# but is 30 units narrower, so the bar's right terminal lands outside the box and shares
# one column of the envelope with a swash diving 133 below the baseline. Read as an arm,
# that column says Z.swsh rises 418 units over its neighbour and swallows it whole, and
# the engulf test threw the pairing out. The same margin MIN_OVERHANG uses to decide what
# counts as an overhang at all decides here where the arm starts.
ARM_MARGIN = MIN_OVERHANG
# How far past the x-height band a letter may reach and still be something an arm can
# arc over (units/em=1000).
#
# Clearance is not the whole question. Sunday Club's l.swsh clears a preceding t by 32
# units and a preceding H by 21, which passes PROTRUSION_LIMIT -- but the arm runs level
# along the top of that ascender for 22 columns, and two near-parallel strokes a fiftieth
# of an em apart read as one tangled stroke, not as an arc. This is what "Atlantic" and
# "Zarathustra" were doing: the l and the h each swung a 270-unit arm back over the t in
# front of them, threading between its ascender and the cap line.
#
# What distinguishes the pairs that work is not how much room is left but what is under
# the arm. This face draws its x-height letters to 366 and everything taller to 435 (t),
# 445 (capitals) or 504 (ascenders), so there is a 69-unit band with nothing in it: an arm
# either has a short letter beneath it, with the whole gap from x-height to its own stroke
# to breathe in, or it has an extender beneath it and no room at all. 40 sits in that band
# with margin on both sides, and is the same allowance MIN_OVERHANG uses for "ink that is
# really there" elsewhere.
#
# Applied to under-sweeps as well, against the foot of the band rather than its top: a
# descender in the way of a tail is the same situation upside down.
ARC_HEADROOM = 40
# Letters whose ink defines the x-height band. Measured from the outlines because OS/2
# cannot be trusted here -- this face reports sxHeight 500, which is nearer its ascender
# (504) than the top of any x-height letter it draws (366).
XHEIGHT_LETTERS = "oxescanumrzvw"
# Extra ink a variant adds *inside* its own advance box, below the plain glyph's floor or
# past its right edge, that counts as a terminal flourish (units/em=1000).
#
# Some of Sunday Club's alternates decorate within the advance rather than overhanging it,
# and the overhang test scores those 0 on both sides and discards them as style
# preferences. That is correct by its own measure -- there is no neighbour for them to
# clear, so there is no context to derive -- but it throws away two real letterforms:
#
#   s.swsh   a tail dropping 64 below the baseline, right edge still inside the advance
#   a.titl   a terminal sweep 164 past plain a's right edge, with the advance widened
#            152 to hold it, so it reaches over nothing
#
# Both have the same natural home. A flourish reads as deliberate at the end of a word and
# as a stray mark in the middle of one, so they go word-final -- the one placement the
# geometry cannot argue with, and one that fires at most once per word.
#
# 50 admits exactly those two in this face. Lowering it to 40 also pulls in y.salt, whose
# extra depth comes not from a tail on the same skeleton but from a wholly redrawn y
# (straight tail, 40 units narrower) -- mixing it in would put two different y shapes in
# one line, so it stays above the bar.
MIN_FLOURISH = 50

# Variants placed word-finally by name, because their difference is one the column
# envelope cannot see at all: the fit test treats a glyph as a solid silhouette, which is
# what makes it safe for collisions but blind to anything interior.
FINAL_VARIANTS: set[str] = set()

# Variants that simply become the letter, substituted unconditionally.
#
# e.swsh is not a flourish at all: same advance, same silhouette to within 1 unit/em, no
# overhang, no tail. What differs is interior -- the bar detaches from the bowl and the
# aperture opens (2.7% of the ink moves, all of it at that junction). That is a letterform
# preference rather than a contextual fix, so there is no context worth deriving; it reads
# as the face's own e and is used everywhere.
#
# Emitted as a plain single substitution in a lookup that runs after everything else, which
# is what keeps it from interfering: the contextual rules above name plain `e` in their
# neighbour classes, and they have all had their say by the time this fires. The vendor's
# kern classes already cover e.swsh (identical values for every pair tested), so spacing is
# unaffected. Sunday Club is only used on h1/h2, which inherit `font-feature-settings:
# "liga", "calt"`, so calt is never off where this matters.
# C.swsh joins it for a different reason. Its spiral terminal is drawn wholly inside the
# advance -- no overhang, no tail, nothing past plain C's own edges -- so the fit test
# scores it 0 on every measure and has nothing to say about where it belongs. Unlike
# e.swsh it is unmistakably a decorated letter rather than a preference, but a capital in
# a heading is about one per word and almost always leads it, which is the classic place
# for a swash and the placement the reference setting uses. There is no context to derive,
# so it is a choice, and the choice is to use it.
# i.salt is e.swsh's case exactly, and even less visible to the fit test. Same advance
# (217), same bounding box to the unit, so the column envelope cannot tell the two apart
# at all -- the difference is that the tittle joins the stem, one continuous contour from
# baseline to 504 instead of a stem and a detached dot, which moves 1.8% of the ink and
# nothing else. The vendor puts i and i.salt in the same kern class on both sides, so
# spacing is untouched. Nothing to derive, so it is a choice: the joined i is the one the
# site uses.
ALWAYS_VARIANTS: set[str] = {"e.swsh", "C.swsh", "i.salt"}

# Escape hatches for dropping a variant out of the automatic set (each stays reachable
# through the .salt/.swsh/.titl CSS classes). All empty: everything the font draws is a
# candidate and the fit test decides.
#
# ss01-ss04 are worth keeping in particular because that is where Sunday Club hides the
# intermediate arms. Its t has seven forms, five reaching left (alt3 156, alt2 192, titl
# 204, alt1 300, swsh 340) and two reaching right (alt4 303, salt 335), which is a range
# of lengths for a range of neighbours, not seven ways to draw the same letter. Excluding
# a feature punches a hole in that ladder that nothing else can fill.
EXCLUDE_VARIANTS: set[str] = set()
EXCLUDE_FEATURES: set[str] = set()
EXCLUDE_BASES: set[str] = set()

# Which letters may be swashed automatically. Empty means every letter is eligible.
#
# calt matches positions, it cannot count, so there is no way to say "at most two swashes
# per word" -- every eligible position whose neighbours tuck will fire. This set is the
# only density control there is. It is currently open: the fit test is strict enough that
# the extra lowercase bases (a b d h l m n p q r u v w) contribute 21 more rules, all of
# them positions where the neighbour genuinely sits inside the swash.
#
# Pass --sparse for the restrained version -- capitals, which are naturally about one per
# word and the classic place for a swash, plus the lowercase letters whose extenders are
# this face's signature.
AUTO_BASES: set[str] = set()

SPARSE_BASES: set[str] = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") | {
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
        self.x_top, self.x_bottom = self._xheight_band()

    def _xheight_band(self) -> tuple[float, float]:
        """The top and floor of this face's x-height letters, from their outlines."""
        tops, bottoms = [], []
        for g in XHEIGHT_LETTERS:
            cols = self.columns(g) if g in self.hmtx.metrics else None
            if not cols:
                continue
            tops.append(max(v[1] for v in cols.values()))
            bottoms.append(min(v[0] for v in cols.values()))
        if not tops:
            return self.xheight, 0.0
        return max(tops), min(bottoms)

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

    def overhang_ink(self, name: str, side: str, base: str | None = None,
                     margin: float = 0.0) -> dict[int, list[float]]:
        """Only the ink the variant adds beyond the plain glyph it replaces.

        Measuring from the advance box alone is not enough: plain `f` already pokes
        9 units left of its origin, and that sliver of ordinary sidebearing sits low
        enough to look like a collision with whatever precedes it -- which wrongly
        disqualified `o` before `f.swsh`, the very pairing in "Hofer". The swash is
        the ink the variant adds, so the plain glyph's own overhang is the baseline.

        `margin` pushes the cut further out still; see arm_ink.
        """
        cols = self.columns(name)
        pad_l, pad_r = self.overhang(base) if base else (0.0, 0.0)
        if side == "L":
            return {k: v for k, v in cols.items() if (k + 1) * COLUMN <= -(pad_l + margin)}
        edge = self.advance(name) + pad_r + margin
        return {k: v for k, v in cols.items() if k * COLUMN >= edge}

    def arm_ink(self, name: str, side: str,
                base: str | None = None) -> dict[int, list[float]]:
        """The overhang with its innermost ARM_MARGIN dropped -- the arm proper.

        Right at the advance the envelope stops telling arm from letter: one column can
        hold both a body terminal and the swash passing beneath it, and a test that reads
        the column as a single span reads the pair as one enormous stroke. Everything that
        asks *where the arm points* rather than *how much room it needs* works from here.
        """
        return self.overhang_ink(name, side, base, margin=ARM_MARGIN)

    def orientation(self, name: str, side: str, base: str | None = None) -> int:
        """+1 if the overhang arcs over its neighbours, -1 if it sweeps beneath them."""
        ink = self.arm_ink(name, side, base) or self.overhang_ink(name, side, base)
        if not ink:
            return 1
        # Judged at the tip, over the outer third of the arm's columns, and by the median
        # of their midpoints rather than the bounding box. Both narrowings matter. An arm
        # dips back to the baseline where it rejoins the stem, so a min/max midpoint reads
        # overhead arcs as level; and the columns nearest the stem hold the letter itself,
        # so averaging over the whole arm reads A.swsh -- whose curl sits at 300 but whose
        # own left leg shares its columns -- as sweeping under, which cost it every
        # neighbour it had and the word-initial placement the face draws it for.
        order = sorted(ink)
        tip = order[:max(1, len(order) // 3)] if side == "L" \
            else order[-max(1, len(order) // 3):]
        mids = sorted((ink[k][0] + ink[k][1]) / 2 for k in tip)
        return 1 if mids[len(mids) // 2] >= self.xheight / 2 else -1

    def protrusion(self, variant: str, neighbour: str, side: str,
                   base: str | None = None) -> float:
        """How far a neighbour escapes the overhang's silhouette.

        Negative means the neighbour stays tucked inside; positive means it pokes
        out past the swash. Returns -inf when the two never share a column.
        """
        ink = self.overhang_ink(variant, side, base)
        if not ink:
            return float("-inf")
        # Engulfment is a question about the arm, so it is asked only of the arm's own
        # columns. The clearance measurement stays on the full overhang: every unit of
        # ink outside the box has a neighbour under it and has to fit.
        arm = self.arm_ink(variant, side, base)
        cols = self.columns(neighbour, self.offset(variant, neighbour, side))
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
                if k in arm and amin < bmin - ENGULF_SLACK:
                    return float("inf")
                worst = max(worst, bmax - amax)
            else:
                if k in arm and amax > bmax + ENGULF_SLACK:
                    return float("inf")
                worst = max(worst, amin - bmin)
        return worst

    def offset(self, variant: str, neighbour: str, side: str) -> float:
        """Where the neighbour's origin sits in the variant's own coordinate frame."""
        if side == "R":
            return self.advance(variant) + self.kern(variant, neighbour)
        return -(self.advance(neighbour) + self.kern(neighbour, variant))

    def obstructs(self, variant: str, neighbour: str, side: str,
                  base: str | None = None) -> bool:
        """Whether the neighbour is too tall (or too deep) for the arm to arc over it.

        A different question from protrusion, which asks whether the two outlines clear
        each other and answers it in units. This asks whether there was ever room for the
        arm to be there: an arm passing over an ascender has the 138 units between
        x-height and ascender taken away from it before it starts, and what is left is a
        gap too fine to read as one stroke arcing over another. See ARC_HEADROOM.

        Asked of the arm's own columns only. The innermost columns of an overhang hold the
        variant's own body, and the letter it replaced stood next to that same extender
        quite happily.
        """
        arm = self.arm_ink(variant, side, base)
        if not arm:
            return False
        cols = self.columns(neighbour, self.offset(variant, neighbour, side))
        over = self.orientation(variant, side, base) > 0
        for k in arm:
            span = cols.get(k)
            if span is None:
                continue
            if over and span[1] > self.x_top + ARC_HEADROOM:
                return True
            if not over and span[0] < self.x_bottom - ARC_HEADROOM:
                return True
        return False

    def band(self, name: str, side: str, base: str | None = None):
        """Vertical extent of an arm, or None if the glyph has none on that side."""
        ink = self.arm_ink(name, side, base)
        if not ink:
            return None
        return min(v[0] for v in ink.values()), max(v[1] for v in ink.values())

    def tucks(self, variant: str, neighbour: str, side: str,
              base: str | None = None) -> bool:
        if self.obstructs(variant, neighbour, side, base):
            return False
        return self.protrusion(variant, neighbour, side, base) <= PROTRUSION_LIMIT

    def covers(self, variant: str, neighbour: str, side: str) -> bool:
        """Whether the neighbour is wide enough to sit under the whole overhang.

        An arm does not stop at the letter it was measured against. t.swsh reaches 340
        units left, which is wider than i (217) or l (241), so after those it carries on
        over the letter *beyond* -- one this rule never looked at and, being a single
        position of calt backtrack, cannot look at. That is where most collisions come
        from: an arm cleared its neighbour and landed on the next letter's ascender.

        Requiring the overhang to fit within one neighbour's advance is what makes the
        one-position test sound. It is also what the tucking metaphor already assumed:
        a swash arcs over *a* letter, and one that outruns its neighbour is not arcing
        over anything in particular.
        """
        left, right = self.overhang(variant)
        if side == "R":
            room = self.advance(neighbour) + self.kern(variant, neighbour)
            return right <= room + COVER_SLACK
        room = self.advance(neighbour) + self.kern(neighbour, variant)
        return left <= room + COVER_SLACK

    def descent(self, variant: str, base: str) -> float:
        """How much further below the plain glyph's own floor the variant reaches."""
        cv, cb = self.columns(variant), self.columns(base)
        if not cv or not cb:
            return 0.0
        return min(v[0] for v in cb.values()) - min(v[0] for v in cv.values())

    def right_growth(self, variant: str, base: str) -> float:
        """How much further right of the plain glyph's own edge the variant reaches."""
        cv, cb = self.columns(variant), self.columns(base)
        if not cv or not cb:
            return 0.0
        return (max(cv) - max(cb)) * COLUMN

    def flourish(self, variant: str, base: str) -> float:
        """Decoration the variant adds without overhanging anything.

        Callers reach here only once the overhang test has passed on this variant, so
        whatever extra ink it carries is contained by its own advance and has no
        neighbour to clear -- either hanging below the baseline or sweeping right into
        an advance widened to hold it.
        """
        return max(self.descent(variant, base), self.right_growth(variant, base))


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


# The order the generated lookups are applied in, which is also the order of priority:
# each one sees what the ones before it drew, and can be written in terms of the glyphs
# they leave behind.
#
#   initial  a word-initial swash for the first letter of the run, which no backtrack
#            class can reach -- there is nothing before it to name
#   arms     every variant that reaches left, the long decoration this face is for
#   tails    word-final flourishes drawn inside their own advance
#   nubs     variants that only reach right, the short ones
#   fallback the vendor's own defensive calt rules
#   restyle  ALWAYS_VARIANTS
#
# Arms before nubs is the substantive ordering, and it is what the reference setting does:
# in "Atlantic" the t swings a 340-unit arm back over the n, and the price is plain a and
# plain n, because a right nub on the a would be arcing over that same n from the other
# side. Deriving them in one pass made that a race the nub won by sitting earlier in the
# word; deriving arms first makes it a decision, and 340 units of swash beats 86.
#
# The split pays a second time in precision. A rule's lookahead cannot see rules that have
# not run yet, so a one-pass derivation has to assume the letter ahead may still turn into
# any shape it has -- which is why plain `a` was refused after Z.salt on account of a.titl,
# a form that only ever appears at the end of a word. By the time `nubs` runs, arms and
# tails have both had their say, so its lookahead names the glyph that will actually be
# drawn.
STAGES = ("initial", "arms", "tails", "nubs", "fallback", "restyle")


class Rule:
    def __init__(self, base, variant, feature, over_l, over_r, left, right,
                 flourish=0.0, final=False, always=False):
        self.base = base
        self.variant = variant
        self.feature = feature
        self.over_l = over_l
        self.over_r = over_r
        self.left = left          # allowed preceding glyphs (None = unconstrained)
        self.right = right        # allowed following glyphs (None = unconstrained)
        self.flourish = flourish  # decoration added inside the variant's own advance
        self.final = final        # fires only where no letter follows
        self.always = always      # fires everywhere, no context at all

    @property
    def stage(self):
        """Which generated lookup this rule belongs in."""
        if self.always:
            return "restyle"
        if self.final:
            return "tails"
        return "arms" if self.over_l >= MIN_OVERHANG else "nubs"

    @property
    def word_initial(self):
        """Whether this rule is also wanted at the very start of the run."""
        return self.stage == "arms" and self.left is not None and "space" in self.left

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
        # Cased letters only. Unicode also files the spacing modifiers under L, but
        # a modifier letter never stands next to a letter inside a word, so admitting
        # them just invents contexts: a.alt1's entire right-hand class came out as
        # [circumflex], a rule that can never match.
        if unicodedata.category(chr(cp)) in ("Ll", "Lu", "Lt") and "." not in name:
            out.append(name)
    return sorted(set(out))


def variant_stage(geom: Geometry, base: str, var: str, tail_variants: set[str]):
    """Which lookup would emit this variant, or None if nothing ever will.

    Decided from geometry alone rather than from the derived rules, so it can be used
    while deriving them. It is a superset of what is actually emitted -- a variant may
    still turn out to have no neighbour that fits -- which is the safe direction: a
    lookahead class that allows for a shape that never appears only declines a pairing
    that would have been fine.
    """
    if var in EXCLUDE_VARIANTS or base in EXCLUDE_BASES:
        return None
    if var in ALWAYS_VARIANTS:
        return "restyle"
    if var in tail_variants:
        return "tails"
    over_l, over_r = geom.overhang(var)
    base_l, base_r = geom.overhang(base)
    if over_l - base_l >= MIN_OVERHANG:
        return "arms"
    if over_r - base_r >= MIN_OVERHANG:
        return "nubs"
    return None


class Cast:
    """Which glyphs each lookup may find to its left and to its right.

    Both sides of a calt match are shapes rather than letters, and the two sides go wrong
    in opposite directions. To the left the lookup sees what the passes before it drew --
    a class written in plain letters would forbid a swash after any letter that took one,
    which is most of the alphabet: "Atlantic" used to lose the arm on its t purely because
    the A in front of it had turned into A.swsh first. To the right nothing has run yet
    within the same lookup, so a letter can only be named as itself, and it may still be
    swapped for something taller by a lookup further down the list -- there the sets are
    used the other way round, and a letter qualifies only if every shape still open to it
    clears the arm.
    """

    def __init__(self, geom: Geometry, variants, neighbours, ligatures, tail_variants):
        self.plain = sorted(set(neighbours) | set(ligatures))
        self.by_stage: dict[str, dict[str, list[str]]] = {s: defaultdict(list)
                                                          for s in STAGES}
        for base in variants:
            if base not in set(neighbours):
                continue
            for var in set(variants[base].values()):
                stage = variant_stage(geom, base, var, tail_variants)
                if stage:
                    self.by_stage[stage][base].append(var)

    def produced(self, *stages) -> list[str]:
        return sorted(v for s in stages for vs in self.by_stage[s].values() for v in vs)

    def preceding(self, *stages) -> list[str]:
        """Every glyph that can lead a match once `stages` have run."""
        return sorted(set(self.plain) | set(self.produced(*stages)))

    def following(self, *stages) -> dict[str, list[str]]:
        """Glyph -> every shape it can still take, given `stages` are yet to run.

        Keyed by the glyph as the lookahead will name it, which for a lookup that runs
        after others includes the variants those others produced.
        """
        out: dict[str, list[str]] = {}
        for g in self.plain:
            out[g] = [g] + [v for s in stages for v in self.by_stage[s].get(g, [])]
        return out


def contextual_rules(geom: Geometry, variants, cast: Cast) -> list[Rule]:
    """The overhang rules, each derived against the cast its own lookup will see."""
    # `arms` runs first, so only the letters themselves and its own output can precede a
    # match; and anything can still follow, bar the word-final flourishes, which are
    # guarded in `tails` instead (see render_fea).
    preceding = {"arms": cast.preceding("initial", "arms"),
                 "nubs": cast.preceding("initial", "arms", "tails", "nubs")}
    following = {"arms": cast.following("initial", "arms", "restyle"),
                 "nubs": cast.following("nubs", "restyle")}
    # nubs looks ahead at glyphs, not letters: arms and tails have already drawn, so those
    # forms are settled and name themselves. Its own output is not -- the pass walks left
    # to right, so the letter under this arm can still take a nub of its own afterwards.
    for g in cast.produced("initial", "arms", "tails"):
        following["nubs"][g] = [g]

    rules: list[Rule] = []
    for base in sorted(variants):
        if base in EXCLUDE_BASES:
            continue
        if AUTO_BASES and base not in AUTO_BASES:
            continue
        candidates = []
        seen: set[str] = set()
        for tag, var in variants[base].items():
            if tag in EXCLUDE_FEATURES or var in EXCLUDE_VARIANTS:
                continue
            # A face may reach one drawing through several features -- Sunday Club's
            # a.alt1 is both salt and ss01. Keep the first, highest-priority tag; the
            # second would emit a byte-identical rule that the first always wins.
            if var in seen:
                continue
            seen.add(var)
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

        # Contexts already taken by a higher-priority rule for this letter. calt is
        # first-match-wins, so a rule whose context is wholly inside an earlier one can
        # never fire, and shipping it is dead weight in an inlined critical asset.
        # Sunday Club's t.alt4 is the case in point: a right arm 32 units shorter than
        # t.salt, which clears every neighbour t.alt4 clears and clears them by more.
        # Nothing in the geometry ever picks it, so it is a choice between two lengths
        # rather than a fit, and the fit test should say so instead of emitting a rule
        # that quietly never matches.
        claimed_l: set[str] = set()
        claimed_r: set[str] = set()

        for tag, var, over_l, over_r in candidates:
            left = right = None
            stage = "arms" if over_l >= MIN_OVERHANG else "nubs"

            if over_l >= MIN_OVERHANG:
                left = [n for n in preceding[stage]
                        if geom.tucks(var, n, "L", base) and geom.covers(var, n, "L")]
                # Word-initial needs a short reach *and* an overhead arc. A descender
                # sweep (j.titl) drawn under an empty gap bridges the two words at the
                # baseline, the same stray mark as a long arc drawn over one.
                #
                # Tested before the class is checked for emptiness, not after: A.swsh
                # is drawn to lead a word and nothing else -- its curl starts where a
                # preceding letter would end -- so the geometry rejects every letter and
                # the gap is the only context it has.
                if (ALLOW_WORD_INITIAL
                        and over_l <= WORD_INITIAL_MAX_REACH
                        and geom.orientation(var, "L", base) > 0):
                    left = ["space"] + left
                if not left:
                    continue

            if over_r >= MIN_OVERHANG:
                forms = following[stage]
                right = [n for n in sorted(forms)
                         if all(geom.tucks(var, g, "R", base) and geom.covers(var, g, "R")
                                for g in forms[n])]
                if not right:
                    continue

            if (left is not None and set(left) <= claimed_l) or \
               (right is not None and set(right) <= claimed_r):
                continue
            if left is not None and right is None:
                claimed_l |= set(left)
            if right is not None and left is None:
                claimed_r |= set(right)

            rules.append(Rule(base, var, tag, over_l, over_r, left, right))
    return rules


def derive_rules(geom: Geometry, variants, neighbours, ligatures) -> list[Rule]:
    """Every rule, in the order its lookup is applied."""
    finals = derive_final_rules(geom, variants, neighbours)
    cast = Cast(geom, variants, neighbours, ligatures, {r.variant for r in finals})
    rules = contextual_rules(geom, variants, cast)
    rules.extend(finals)
    rules.extend(derive_always_rules(geom, variants))
    rules.sort(key=lambda r: (STAGES.index(r.stage), -r.weight, -r.flourish, r.base))
    return rules, cast


def derive_always_rules(geom: Geometry, variants) -> list[Rule]:
    """The ALWAYS_VARIANTS, as unconditional substitutions."""
    out: list[Rule] = []
    for base in sorted(variants):
        if base in EXCLUDE_BASES:
            continue
        for tag, var in variants[base].items():
            if var in ALWAYS_VARIANTS:
                out.append(Rule(base, var, tag, 0.0, 0.0, None, None, always=True))
    return out


def derive_final_rules(geom: Geometry, variants, neighbours) -> list[Rule]:
    """Variants placed word-finally: tails, plus the hand-picked ones in FINAL_VARIANTS.

    Deliberately not filtered by AUTO_BASES: that set exists to keep swashes from firing
    several times a word, and a word-final rule can fire at most once per word by
    construction, so it needs no density budget of its own.
    """
    letters = set(neighbours)
    out: list[Rule] = []
    for base in sorted(variants):
        if base in EXCLUDE_BASES or base not in letters:
            continue
        best = None
        for tag, var in variants[base].items():
            if tag in EXCLUDE_FEATURES or var in EXCLUDE_VARIANTS:
                continue
            if var in ALWAYS_VARIANTS:
                continue
            over_l, over_r = geom.overhang(var)
            base_l, base_r = geom.overhang(base)
            if max(over_l - base_l, over_r - base_r) >= MIN_OVERHANG:
                continue  # an overhang: the contextual rules already had their say
            reach = geom.flourish(var, base)
            if reach < MIN_FLOURISH and var not in FINAL_VARIANTS:
                continue
            key = (-reach, FEATURE_PRIORITY.index(tag))
            if best is None or key < best[0]:
                best = (key, tag, var, reach)
        if best:
            _, tag, var, reach = best
            out.append(Rule(base, var, tag, 0.0, 0.0, None, None,
                            flourish=reach, final=True))
    return out


# --- .fea emission -----------------------------------------------------------


def fmt_class(glyphs) -> str:
    return "[" + " ".join(glyphs) + "]"


def bands_meet(a, b) -> bool:
    """Whether two vertical extents come close enough to read as a collision.

    Same bar as the fit test: PROTRUSION_LIMIT is how far one stroke must stay clear of
    another, so two arms that leave each other less than that have met.
    """
    if a is None or b is None:
        return False
    return min(a[1], b[1]) - max(a[0], b[0]) > PROTRUSION_LIMIT


def reach_band(geom: Geometry, glyph: str, side: str):
    """Vertical extent of whatever `glyph` reaches outside its own advance box.

    Measured from the box and not, as the fit test does, from the plain letter's own
    overhang. The two questions are different: the fit test asks what decoration a variant
    adds, and can discount the sidebearing its letter always had, whereas this asks what
    ink of it lands in the next letter's box -- and the hook `f` is simply drawn with,
    67 units past its advance, lands there as squarely as any swash. Netting it off left
    f and its variants out of the guard entirely.
    """
    return geom.band(glyph, side)


def group_by_conflict(conflicts: dict[str, list[str]]) -> list[tuple[list[str], list[str]]]:
    """Collapse target -> conflicting glyphs into one ignore rule per distinct set."""
    grouped: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for target, others in conflicts.items():
        if others:
            grouped[tuple(sorted(others))].append(target)
    return [(sorted(targets), list(others))
            for others, targets in sorted(grouped.items())]


def one_side_guards(reaching, blocked, word_chars, lookahead: bool):
    """The rule that a letter may be arced over from one side only.

    Geometry.covers keeps each arm inside the one letter it arcs over, which leaves
    exactly one way for two arms to meet: a right arm from two positions back and a left
    arm from here, both reaching into the letter between them. Neither rule can see the
    other -- each looks at one neighbour, and the clash is with the glyph past it -- so it
    has to be stated separately, over two positions.

    Not as a blanket ban, though, because most of those pairs never touch: in "Zarathustra"
    the u drops a tail below the baseline under the s while the t swings an arm over the
    top of it, and reading that as a collision cost the reference setting two of its
    swashes. So the two arms are compared as vertical extents and only the pairs that
    actually meet are suppressed.
    """
    conflicts = {}
    for base, band in blocked.items():
        conflicts[base] = [g for g, gband in reaching.items() if bands_meet(band, gband)]
    out = []
    for targets, others in group_by_conflict(conflicts):
        if lookahead:
            out.append(f"    ignore sub {fmt_class(targets)}' "
                       f"{fmt_class(word_chars)} {fmt_class(others)};\n")
        else:
            out.append(f"    ignore sub {fmt_class(others)} {fmt_class(word_chars)} "
                       f"{fmt_class(targets)}';\n")
    return out


def reshape_guards(geom: Geometry, targets, armed, side: str):
    """Keep a letter under an arm in the shape the arm was measured against.

    An arm and a variant in the letter next to it cannot normally collide -- covers puts
    the arm inside that letter's advance box and the variant's own decoration outside it,
    and those are different places. What breaks that is a variant which changes the box:
    Sunday Club's r.swsh trades 150 units of advance for its arm, so an r that has already
    been arced over by a following t.swsh shrinks under it, dragging the t 150 units left
    and running its arm off the far side of the r into the letter beyond. Every long-range
    collision the audit found came from this. It cuts the other way too, in smaller
    amounts: a.swsh is 20 units narrower than a, which is enough to slide the a out from
    under Z.swsh's tail, and refusing to allow for it is what kept the Z in "Zarathustra"
    plain.

    Asked as the question the arm was derived from -- would this rule still have been
    written if the neighbour had been drawn this way -- so a variant that leaves the
    silhouette and the advance alone passes and keeps its decoration.

    Stated as an ignore in the later lookup rather than by striking those letters out of
    the arms' neighbour classes, because the arm is the decoration worth keeping:
    "aftertask" should swing the t over its r, not go plain to spare the r a nub it can
    have anywhere else.
    """
    conflicts = {}
    for base, variants in targets.items():
        conflicts[base] = sorted(
            arm for arm, arm_base in armed.items()
            if any(not (geom.tucks(arm, v, side, arm_base)
                        and geom.covers(arm, v, side))
                   for v in variants))
    out = []
    for group, others in group_by_conflict(conflicts):
        if side == "L":   # the arm follows, and reaches back over these
            out.append(f"ignore sub {fmt_class(group)}' {fmt_class(others)};\n")
        else:             # the arm precedes, and reaches forward over these
            out.append(f"ignore sub {fmt_class(others)} {fmt_class(group)}';\n")
    return out


def render_fea(geom, features, rules, cast, vendor_calt, word_chars, all_glyphs) -> str:
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

    by_stage = {stage: [r for r in rules if r.stage == stage] for stage in STAGES}

    def emit(r, indent, drop_left=False):
        parts = []
        if r.left is not None and not drop_left:
            parts.append(fmt_class(r.left))
        parts.append(f"{r.base}'")
        if r.right is not None:
            parts.append(fmt_class(r.right))
        w(f"{indent}# {r.base} -> {r.variant} ({r.feature}, "
          f"overhang L{r.over_l:.0f} R{r.over_r:.0f})\n")
        w(f"{indent}sub {' '.join(parts)} by {r.variant};\n")

    # Everything a glyph can reach outside its box by the time `arms` runs: the letters
    # that are simply drawn that way, and the two-sided variants arms itself produces.
    # This is a much smaller set than every swash in the font, and that is the point --
    # the nubs have not been placed yet, so they cannot veto an arm.
    arms_time = sorted(set(word_chars) & (set(cast.plain) | set(cast.produced("arms"))))
    reaching = {g: reach_band(geom, g, "R") for g in arms_time}
    reaching = {g: b for g, b in reaching.items()
                if b is not None and geom.overhang(g)[1] >= MIN_OVERHANG}
    # ...and the base each of those is a variant of, for the reshape guards, which ask
    # the fit test's own question and so need the same baseline it was asked with.
    right_armed = {g: (g.split(".")[0] if g.split(".")[0] in geom.hmtx.metrics else None)
                   for g in reaching}

    w("feature calt {\n")

    # Word-initial swashes for the first letter of the run. Every other position has a
    # glyph before it that a backtrack class can name; the first has nothing, and a class
    # cannot match what is not there -- which is why "Film Festival" swashed its second F
    # and not its first. Stated as the absence of any glyph at all, and placed ahead of
    # everything else so the leading letter gets the most decorative form it can take
    # rather than whatever a one-sided rule offers.
    initial = [r for r in by_stage["arms"] if r.word_initial]
    if initial:
        w("    lookup initial {\n")
        w(f"        @anyglyph = {fmt_class(all_glyphs)};\n")
        for base in sorted({r.base for r in initial}):
            w(f"        ignore sub @anyglyph {base}';\n")
            for r in [r for r in initial if r.base == base]:
                emit(r, "        ", drop_left=True)
        w("    } initial;\n\n")

    w("    lookup arms {\n")
    left_bands = {}
    for r in by_stage["arms"]:
        band = geom.band(r.variant, "L", r.base)
        if band is None:
            continue
        have = left_bands.get(r.base)
        left_bands[r.base] = band if have is None else (min(have[0], band[0]),
                                                        max(have[1], band[1]))
    for line in one_side_guards(reaching, left_bands, word_chars, lookahead=False):
        w("    " + line)
    if left_bands:
        w("\n")
    for r in by_stage["arms"]:
        emit(r, "        ")
    w("    } arms;\n")

    # Tails run before the nubs and after the arms. After, so a letter that already earned
    # a swash keeps it -- by then the glyph is no longer the plain one these rules match.
    # Before, so that the nubs' lookahead can name the flourished glyph outright instead of
    # refusing every letter that might one day end a word: plain `a` after Z.salt was
    # refused on account of a.titl, which only ever appears at the end of one.
    #
    # "No letter follows" is stated as an ignore rather than a lookahead class because a
    # lookahead cannot match the end of the run, which is exactly where a word ending a
    # heading sits. @wordchar therefore has to include the variant glyphs too: the arms
    # lookup may already have replaced the letter after this one.
    final = by_stage["tails"]
    if final:
        w("\n    lookup tails {\n")
        w(f"        @wordchar = {fmt_class(word_chars)};\n")
        for r in final:
            why = (f"flourish {r.flourish:.0f} inside its own advance"
                   if r.flourish >= MIN_FLOURISH
                   else "interior difference, opted in by name")
            w(f"        # {r.base} -> {r.variant} ({r.feature}, {why}, word-final only)\n")
            # A flourish drawn inside the advance still shares that space with an arm
            # swung over the letter from behind, so it defers to one it would displace.
            for line in reshape_guards(geom, {r.base: [r.variant]}, right_armed, "R"):
                w("        " + line)
            w(f"        ignore sub {r.base}' @wordchar;\n")
            w(f"        sub {r.base}' by {r.variant};\n")
        w("    } tails;\n")

    nubs = by_stage["nubs"]
    if nubs:
        w("\n    lookup nubs {\n")
        right_bands = {}
        for r in nubs:
            band = geom.band(r.variant, "R", r.base)
            if band is None:
                continue
            have = right_bands.get(r.base)
            right_bands[r.base] = band if have is None else (min(have[0], band[0]),
                                                             max(have[1], band[1]))
        # The mirror of the guard in `arms`, and the reason it can be exact: the arms are
        # already drawn, so the letter two ahead is named by the variant it became rather
        # than by the letter it was typed as.
        left_armed = {g: g.split(".")[0] for g in cast.produced("arms")
                      if geom.overhang(g)[0] - geom.overhang(g.split(".")[0])[0]
                      >= MIN_OVERHANG}
        placed = {g: reach_band(geom, g, "L") for g in left_armed}
        placed = {g: b for g, b in placed.items() if b is not None}
        by_base = defaultdict(list)
        for r in nubs:
            by_base[r.base].append(r.variant)
        for line in reshape_guards(geom, by_base, left_armed, "L"):
            w("        " + line)
        for line in reshape_guards(geom, by_base, right_armed, "R"):
            w("        " + line)
        for line in one_side_guards(placed, right_bands, word_chars, lookahead=True):
            w("    " + line)
        if right_bands:
            w("\n")
        for r in nubs:
            emit(r, "        ")
        w("    } nubs;\n")

    if vendor_calt:
        w("\n    lookup fallback {\n")
        w("        # Vendor rules, kept as a fallback for pairs that collide.\n")
        for back, g, ahead, sub in vendor_calt:
            parts = [fmt_class(c) for c in back] + [f"{g}'"] + [fmt_class(c) for c in ahead]
            w(f"        sub {' '.join(parts)} by {sub};\n")
        w("    } fallback;\n")

    # Last of all, so every rule above still sees the plain letters its neighbour classes
    # are written in terms of.
    always = by_stage["restyle"]
    if always:
        w("\n    lookup restyle {\n")
        for r in always:
            w(f"        # {r.base} -> {r.variant} ({r.feature}, unconditional)\n")
            w(f"        sub {r.base} by {r.variant};\n")
        w("    } restyle;\n")
    w("} calt;\n")
    return out.getvalue()


def ligature_glyphs(features, neighbours) -> list[str]:
    """Glyphs liga/dlig build out of letters, which can therefore lead a calt match."""
    letters = set(neighbours)
    out = []
    for tag in ("liga", "dlig"):
        for lk in features.get(tag, []):
            for comps, lig in lk.ligatures:
                if all(c in letters for c in comps):
                    out.append(lig)
    return sorted(set(out))


def word_glyphs(font: TTFont, neighbours) -> list[str]:
    """Every glyph that continues a word: letters, their variants, ligatures, apostrophes.

    An apostrophe counts as part of the word, so "day\u2019s" keeps its plain first s.
    """
    letters = set(neighbours)
    out = {g for g in font.getGlyphOrder()
           if g.split(".")[0].split("_")[0] in letters}
    order = set(font.getGlyphOrder())
    out |= {g for g in ("quotesingle", "quoteright") if g in order}
    return sorted(out)


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
    print(f"{'base':>6}  {'variant':<16}{'feat':<6}{'lookup':<9}{'overL':>7}{'overR':>7}"
          f"{'left':>7}{'right':>7}  needs")
    for r in rules:
        needs = []
        if r.word_initial:
            needs.append("word-initial")
        if r.left is not None:
            needs.append("left")
        if r.right is not None:
            needs.append("right")
        if r.final:
            needs.append(f"word-final (flourish {r.flourish:.0f})"
                         if r.flourish >= MIN_FLOURISH else "word-final (interior)")
        if r.always:
            needs.append("everywhere")
        print(f"{r.base:>6}  {r.variant:<16}{r.feature:<6}{r.stage:<9}"
              f"{r.over_l:>7.0f}{r.over_r:>7.0f}"
              f"{len(r.left) if r.left else 0:>7}{len(r.right) if r.right else 0:>7}"
              f"  {'+'.join(needs)}")
    counts = {stage: sum(1 for r in rules if r.stage == stage) for stage in STAGES}
    print(f"\n{len(rules)} contextual rules  ("
          + ", ".join(f"{k} {v}" for k, v in counts.items() if v) + ")")


def main() -> int:
    global PROTRUSION_LIMIT, AUTO_BASES
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="print derived rules, write nothing")
    ap.add_argument("--debug", metavar="VARIANT",
                    help="show per-neighbour gaps for one variant glyph, e.g. f.swsh")
    ap.add_argument("--sparse", action="store_true",
                    help="restrict swashes to SPARSE_BASES instead of every letter")
    ap.add_argument("--protrusion", type=float, default=PROTRUSION_LIMIT,
                    help=f"max protrusion past the swash, font units "
                         f"(default {PROTRUSION_LIMIT}; lower is stricter)")
    ap.add_argument("--fea", action="store_true", help="write the .fea and stop")
    ap.add_argument("--fea-in", type=Path, help="compile this .fea instead of generating one")
    args = ap.parse_args()
    PROTRUSION_LIMIT = args.protrusion
    if args.sparse:
        AUTO_BASES = SPARSE_BASES

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
                tall = geom.obstructs(args.debug, n, side, dbase)
                mark = "   " if tall or g > PROTRUSION_LIMIT else "ok "
                why = "  no headroom" if tall else ""
                print(f"    {mark}{n:12s} {g:9.1f}{why}")
        return 0

    rules, cast = derive_rules(geom, variants, neighbours,
                               ligature_glyphs(features, neighbours))

    if args.report:
        report(rules, geom)
        return 0

    if args.fea_in:
        fea = args.fea_in.read_text()
    else:
        words = word_glyphs(font, neighbours)
        every = [g for g in font.getGlyphOrder() if g != ".notdef"]
        fea = render_fea(geom, features, rules, cast, vendor_calt, words, every)
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
