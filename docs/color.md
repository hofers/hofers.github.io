# The palette, and the two gamuts it ships in

`_includes/styles/_sass/_colors.scss` is the only place a color is written down. It
compiles to a table of `--color-*` custom properties on `:root`, plus a second, narrower
table under `@media (color-gamut: p3)` where the chromatic entries are re-stated with more
chroma than sRGB can hold. Stylesheets only ever say `var(--color-teal)` and never learn
which of the two they got.

Before this, colors were Sass variables substituted at each use site, so a color existed
only as however many hex literals referenced it. The move to custom properties is what
makes a second gamut possible at all: you cannot swap a value under a media query if the
value was inlined at compile time.

## This is not the same thing as `--ca-space`

`_aberration.scss` also branches on `(color-gamut: p3)`, and the two are unrelated. That
branch picks the space the *compositor adds numbers in*, so that three `plus-lighter`
layers sum back to the text color — it is the inverse of a blend operation, and getting it
wrong produces a visible cast. See [chromatic-aberration.md](chromatic-aberration.md).

This file is about flat, opaque paint, which no engine gets wrong. Nothing here fixes a
bug; it spends gamut that was previously left on the table. The two mechanisms share a
media feature and nothing else, and neither should be changed to match the other.

## The widening rule

For each color: read its lightness, chroma and hue in OKLCh, find the largest chroma sRGB
can hold at that lightness and hue, find the same for Display P3, and scale the chroma by
the ratio.

    C_p3 = C * maxChroma_p3(L, h) / maxChroma_srgb(L, h)

That preserves the color's position *relative to the gamut boundary*. A color authored
at 60% of the chroma sRGB had available comes out at 60% of what P3 has available. It is a
statement about colors in general rather than a table of values chosen for the palette
that happens to be here now, which is the whole point: re-authoring `$palette` is all a new
color scheme needs, and the P3 half follows without anyone touching it.

Lightness and hue are untouched. Only chroma moves.

There is no closed form for the gamut boundary in OKLCh — it is the RGB cube seen from a
space with different geometry — so `_max-chroma()` bisects, 18 iterations, which lands
within 0.5/2^18 of the boundary. Far finer than the four decimals the result is rounded to.

### What the current palette gets

Computed by the same rule, cross-checked against an independent implementation:

| name | sRGB | chroma | widened | gain |
| --- | --- | --- | --- | --- |
| `page` | `#000` | 0.0000 | — neutral | — |
| `red` | `#a8000e` | 0.1876 | 0.2114 | +13% |
| `dark-red` | `#6d020c` | 0.1354 | 0.1525 | +13% |
| `white` | `#fbfeff` | 0.0035 | — neutral | — |
| `off-white` | `#f6f6f6` | 0.0001 | — neutral | — |
| `light-gray` | `#adadad` | 0.0001 | — neutral | — |
| `gray` | `#5a5a5a` | 0.0001 | — neutral | — |
| `dark-gray` | `#4e4e4e` | 0.0001 | — neutral | — |
| `off-black` | `#333` | 0.0000 | — neutral | — |
| `teal` | `#13ffc8` | 0.1753 | 0.1982 | +13% |
| `deep-teal` | `#0e9878` | 0.1167 | 0.1592 | **+36%** |
| `deep-teal-shade` | `#0b735b` | 0.0942 | 0.1284 | **+36%** |
| `heading-secondary` | `#e2e9ea` | 0.0077 | — neutral | — |
| `heading-tertiary` | `#dee5e6` | 0.0077 | — neutral | — |
| `body-primary` | `#c4c9ca` | 0.0058 | — neutral | — |
| `off-white-shade` | `#e2e2e2` | 0.0001 | — neutral | — |
| `h1-glow` | `#a2d8e0` | 0.0566 | 0.0628 | +11% |
| `halo-1` | `#27faf8` | 0.1482 | 0.1910 | **+29%** |
| `halo-2` | `#2767fa` | 0.2291 | 0.2456 | +7% |
| `halo-3` | `#7227fa` | 0.2745 | 0.2941 | +7% |
| `halo-4` | `#e227fa` | 0.2966 | 0.3235 | +9% |
| `halo-5` | `#fa2799` | 0.2513 | 0.2858 | +14% |
| `halo-6` | `#fab027` | 0.1602 | 0.1842 | +15% |
| `halo-7` | `#e6fa27` | 0.2065 | 0.2404 | +16% |
| `halo-8` | `#48fa27` | 0.2730 | 0.3214 | +18% |

Two things worth reading off that table.

The gains are uneven because P3's advantage over sRGB is uneven. It is largest in the
green–cyan corner, which is why `deep-teal` and `halo-1` get two to five times what the
blues and violets get. A palette that moved away from teal would get correspondingly less
out of this, and that would not be a bug.

Every accent was already at 98–100% of the chroma sRGB could give it at its lightness and
hue. That is the condition under which any of this is worth doing: a palette sitting well
inside sRGB has nothing to gain from a wider one, because the widening is proportional and
proportional to a small number is a small number.

## Why near-neutrals are exempt

`$p3-min-chroma: 0.02`. Below it, `_widen()` returns null and the color is not re-stated.

The first reason is that it buys nothing. `heading-secondary` sits at chroma 0.0077, or
11% of what sRGB offers at its lightness; widening it proportionally moves it to 0.0083. No
display resolves that, and it would cost a line in the table on every page.

The second reason is the one that matters. `.aberrate` splits `currentColor` through
`color(from currentColor var(--ca-space) …)`, and `--ca-space` is `srgb` on iOS *even on a
P3 display* — deliberately, because iOS composites in extended sRGB. Headings are exactly
the colors `.aberrate` splits. If `heading-secondary` were widened past sRGB, that split
would run on a color with out-of-range channels on the one platform whose compositor does
not clamp them. Keeping the greys inside sRGB removes the interaction rather than reasoning
about it.

The threshold's exact value is not load-bearing today: the palette's neutrals top out at
0.0077 and its chromatic colors start at 0.0566, so 0.02 sits in an empty gap an order of
magnitude wide. A future palette could land a color near it, and the consequence is mild —
a ~10% chroma change on a barely-tinted color, invisible whichever side it falls.

## Why `oklch()` and not `color(display-p3 …)`

OKLCh is the space the widening is computed in, so emitting it is lossless — no second
conversion between the calculation and the stylesheet. It also degrades in the right
direction: the values are constructed to sit inside P3, so a future display wider than P3
renders them at exactly the intended chroma rather than at its own boundary.

## The `@supports` gate is load-bearing

The P3 block is wrapped in `@supports (color: oklch(0 0 0))`, and removing it breaks the
fallback in a way that is easy to miss.

A custom property accepts any token stream. On an engine without `oklch()`,
`--color-teal: oklch(89% 0.1982 169.6deg)` is stored perfectly happily; the failure comes
later, at `color: var(--color-teal)`, where the substitution produces something invalid.
And an invalid substitution does not fall back to the earlier declaration in the cascade —
the property becomes unset, which for an inherited property like `color` means it inherits.
The heading would not go back to `#e2e9ea`; it would take its parent's color.

Gating the whole block means such an engine never sees the widened values at all and the
sRGB table stands. `@property` with `syntax: "<color>"` would also work, by giving the
invalid value an initial value to fall back to, but it needs support of its own and the
`@supports` gate needs none.

## `declare()` is included exactly once

By `stylish.scss`, which `_layouts/default.html` inlines on every page.

The page-specific stylesheets (`contact.scss`, `portfolio.scss`, `wordle-assistant.scss`,
`blog.scss`, `resume.scss`) are **separate Sass compilations**, inlined into the same
document in their own `<style>` blocks. Sass's rule that a module emits its CSS once holds
within one compilation and cannot help across them, so a second `@include colors.declare()`
anywhere is a second copy of the whole table in the HTML.

This is why `_colors.scss` exports a mixin rather than emitting `:root` at the top level as
a side effect of `@use`. Emitting on `@use` is the obvious design and it would have put the
palette in every page twice.

## What is deliberately not in the palette

Two sets of colors stay as literals, and both exclusions are about ownership rather than
laziness. The palette is *our* color scheme; these are someone else's, and widening them
would make them wrong.

- **`wordle-assistant.scss`** — `#121213`, `#3a3a3c`, `#b59f3b`, `#538d4e` are NYT Wordle's
  tile colors, reproduced so the assistant matches the game it assists. Matching is the
  entire requirement, so a more saturated green is a defect. Its `#5a5a5a` *was* ours and
  has been folded in as `--color-gray`.
- **`_code-highlight.scss`** — a vendored GitHub syntax theme, ~60 colors. Desaturated code
  tones with nearly nothing to gain, and pulling them in would mean maintaining a diff
  against upstream forever.

## Cost

Measured on the built output, brotli quality 11, before and after the refactor:

| page | raw before | raw after | brotli before | brotli after |
| --- | --- | --- | --- | --- |
| `index.html` | 21,256 | 23,472 | 6,059 | 6,564 |
| `contact.html` | 25,366 | 27,680 | 6,751 | 7,234 |
| `wordle-assistant.html` | 217,148 | 219,410 | 51,795 | 52,303 |

About +2.2 KB raw and a near-constant **+500 bytes brotli** per page. Constant because it is
one palette table plus one P3 table, the same on every page; the compressor handles the
repeated `var(--color-…)` at the use sites almost for free.

That is a real cost on a site that inlines its critical CSS and goes to some length over
early hints and edge caching. It buys a palette with one source of truth and a wide-gamut
rendering that follows any future change to it automatically.

## Turning it off, and dialling it back

`$p3-boost` is the control. It interpolates between the authored sRGB chroma and the fully
widened value:

- `$p3-boost: 0` disables widening. `_widen()` returns the color unchanged in chroma, the
  P3 table still emits, and the site is sRGB everywhere. To drop the block entirely, delete
  the `@supports` section of `declare()`.
- `$p3-boost: 1` (current) takes the whole headroom.
- Anything between is a partial. Reach for it if a future palette reads garish on a
  wide-gamut display — most likely in the greens, where the headroom is largest and where
  +36% is a big enough step to be worth looking at rather than assuming.

## Verifying a change

`(color-gamut: p3)` is false in headless Chromium, so a default automated run only ever
exercises the sRGB table — which is worth doing, since it should be byte-identical to what
the site rendered before. For the P3 half, either use a real browser on a wide-gamut
display or launch Chromium with `--force-color-profile=display-p3`.

Reading the values back out of the CSSOM is a cheap check that the block parsed:

```js
[...document.styleSheets].flatMap(s => [...s.cssRules])
  .filter(r => r.conditionText?.includes("oklch"))
```

One trap when eyeballing computed styles: the submit button carries
`transition: background-color 0.2s ease`, so `getComputedStyle` immediately after toggling
`:disabled` returns the color it is transitioning *from*. Wait out the transition or the
derived shade looks like it is not applying when it is.
