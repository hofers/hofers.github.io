# The palette, and the two gamuts it ships in

`_includes/styles/_sass/_colors.scss` is the only place a color is written down. It is
written in OKLCh, at the chroma it should have on a wide-gamut display. It compiles to a
table of `--color-*` custom properties on `:root` holding the sRGB rendering of each, plus a
second table under `@media (color-gamut: p3)` holding the authored values themselves.
Stylesheets only ever say `var(--color-teal)` and never learn which of the two they got.

Colors are custom properties rather than Sass variables because the table a page gets is
chosen at run time, by the cascade, and the derived shades are resolved by the engine
against whichever one won.

The palette is authored at the wide end and derived at the narrow end.

## This is not the same thing as `--ca-space`

`_aberration.scss` also branches on `(color-gamut: p3)`, and the two are unrelated. That
branch picks the space the *compositor adds numbers in*, so that three `plus-lighter`
layers sum back to the text color — it is the inverse of a blend operation, and getting it
wrong produces a visible cast. See [chromatic-aberration.md](chromatic-aberration.md).

This file is about flat, opaque paint, which no engine gets wrong. The two mechanisms share
a media feature and nothing else, and neither should be changed to match the other.

## The narrowing rule

For each color: read its lightness, chroma and hue, find the largest chroma Display P3 can
hold at that lightness and hue, find the same for sRGB, and scale the chroma by the ratio.

    C_srgb = C * maxChroma_srgb(L, h) / maxChroma_p3(L, h)

That preserves the color's position *relative to the gamut boundary*. A color authored at
90% of the chroma P3 had available comes out at 90% of what sRGB has available. It is a
statement about colors in general rather than a table of values chosen for the palette that
happens to be here now, which is the whole point: re-authoring `$palette` is all a new color
scheme needs, and the sRGB half follows without anyone touching it.

Lightness and hue are the authored digits, passed through untouched. Only chroma moves, so
the two tables differ in exactly one channel.

There is no closed form for the gamut boundary in OKLCh — it is the RGB cube seen from a
space with different geometry — so `_max-chroma()` bisects, 18 iterations, which lands
within 0.5/2^18 of the boundary. Far finer than the four decimals the result is rounded to.

### What the current palette gives up in sRGB

The cut is uneven, because P3's advantage over sRGB is uneven. It is widest in the
green–cyan corner and nearly absent in the blues and violets: `deep-teal` loses 27% of its
chroma on an sRGB display, `cyan` and `deep-cyan` 26%, while `halo-3` — a violet — loses
2%. A palette that moved away from teal would lose correspondingly less, and that would not
be a bug.

Every accent is authored at 89–100% of the chroma P3 can give it at its lightness and hue.
That is the condition under which any of this is worth doing: a palette sitting well inside
P3 would narrow to almost the same numbers, because the scaling is proportional, and
proportional to a small number is a small number. `h1-glow` is the case that shows it — at
39% of the boundary it is a tint rather than an accent, and the two tables hand it 0.0628
and 0.0565, a difference nobody will see.

The per-color numbers are not reproduced here. They are `$palette` and the two `--color-*`
tables the build emits from it, and a copy in prose would only drift from them.

## The derived shades

`deep-teal-shade`, `deep-cyan-shade` and `off-white-shade` are not values. They are
relative-color declarations naming their source:

```css
--color-deep-cyan-shade: oklch(from var(--color-deep-cyan) calc(l - 0.08) calc(c * 0.87) h);
```

`var()` is substituted after the cascade has chosen a table, so one declaration serves both
gamuts and neither table carries a shade entry. On an sRGB display the engine derives it
from chroma 0.1052; on a P3 display, from 0.1422. Adding a shade is a line in `$shades`,
and it works for any palette entry without anything being computed at build time.

Two details in that declaration are load-bearing.

`l` is a number in 0–1, not a percentage, so `calc(l - 0.08)` is eight points of lightness.

Chroma is **scaled, not held**. A gamut's boundary contracts as lightness drops and the
palette's accents sit on it, so a step at constant chroma walks straight out of gamut —
`deep-teal` at 0.1592 against a boundary that is 0.1412 eight points darker. `$shade-chroma`
approximates that contraction; where it still overshoots, the engine gamut-maps, which is a
graceful failure rather than a wrong color.

One uniform step cannot reproduce a per-color hand-picked shade. If one of these ever needs
to be exact, give it its own `$palette` entry rather than bending the step.

This is the one thing here that needs more than `oklch()` itself: relative color syntax is
Safari 16.4, Chrome 119, Firefox 128.

## Why near-neutrals are exempt

`$p3-min-chroma: 0.02`. Below it, `_narrow()` returns null and the color is emitted once,
identically in both tables.

The first reason is that it buys nothing. `heading-secondary` sits at chroma 0.0076, or 11%
of what P3 offers at its lightness; narrowing it proportionally moves it to 0.0069. No
display resolves that, and it would cost a line in the table on every page.

The second reason is the one that matters. `.aberrate` splits `currentColor` through
`color(from currentColor var(--ca-space) …)`, and `--ca-space` is `srgb` on iOS *even on a
P3 display* — deliberately, because iOS composites in extended sRGB. Headings are exactly
the colors `.aberrate` splits. If `heading-secondary` were authored past sRGB, that split
would run on a color with out-of-range channels on the one platform whose compositor does
not clamp them. Keeping the greys inside sRGB removes the interaction rather than reasoning
about it.

The threshold's exact value is not load-bearing today: the palette's neutrals top out at
0.0152 and its chromatic colors start at 0.0628, so 0.02 sits in an empty gap. A future
palette could land a color near it, and the consequence is mild — a ~10% chroma change on a
barely-tinted color, invisible whichever side it falls.

## Why `oklch()` and not `color(display-p3 …)`

OKLCh is the space the palette is authored in and the space the narrowing is computed in, so
emitting it is lossless — no conversion anywhere between the source and the stylesheet. It
also degrades in the right direction: the authored values sit inside P3, so a future display
wider than P3 renders them at exactly the intended chroma rather than at its own boundary.

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
laziness. The palette is *our* color scheme; these are someone else's, and restating them
in a wider gamut would make them wrong.

- **`wordle-assistant.scss`** — `#121213`, `#3a3a3c`, `#b59f3b`, `#538d4e` are NYT Wordle's
  tile colors, reproduced so the assistant matches the game it assists. Matching is the
  entire requirement, so a more saturated green is a defect. Its `#5a5a5a` *was* ours and
  has been folded in as `--color-gray`.
- **`_code-highlight.scss`** — a vendored GitHub syntax theme, ~60 colors. Desaturated code
  tones with nearly nothing to gain, and pulling them in would mean maintaining a diff
  against upstream forever.

## Cost

The two tables are the same on every page, so what they cost is near-constant: about
2.8 KB raw and **~500 bytes brotli** per page over inlining literals at each use site. The
compressor handles the repeated `var(--color-…)` at the use sites, and the repeated
`oklch(`/`deg)`, almost for free.

That is a real cost on a site that inlines its critical CSS and goes to some length over
early hints and edge caching. It buys a palette with one source of truth and an sRGB
fallback that follows any future change to it automatically.

## Turning it off, and dialling it back

`$p3-boost` is the control. It interpolates the wide-gamut table between the derived sRGB
chroma and the authored value:

- `$p3-boost: 0` collapses the two tables. Every color renders at its sRGB chroma
  everywhere. To drop the block entirely, delete the `@media` section of `declare()`.
- `$p3-boost: 1` (current) takes the authored chroma as written.
- Anything between is a partial. Reach for it if the palette reads garish on a wide-gamut
  display and you want to test that before re-authoring — most likely in the greens, where
  the gap between the two gamuts is largest.

## Verifying a change

The cheapest check on a palette edit is to compile `declare()` on its own and diff:

```bash
printf '@use "colors";\n@include colors.declare();\n' > /tmp/decl.scss
bundle exec ruby -e 'require "sass-embedded"; \
  puts Sass.compile("/tmp/decl.scss", style: :compressed, \
                    load_paths: ["_includes/styles/_sass"]).css'
```

Any entry you did not mean to touch should come out byte-identical, and every entry in the
P3 block should differ from its base entry in chroma alone.

`(color-gamut: p3)` is false in headless Chromium, so a default automated run only ever
exercises the base table. For the P3 half, either use a real browser on a wide-gamut display
or launch Chromium with `--force-color-profile=display-p3`.

Reading the values back out of the CSSOM is a cheap check that the block parsed:

```js
[...document.styleSheets].flatMap(s => [...s.cssRules])
  .filter(r => r.conditionText?.includes("color-gamut"))
```

One trap when eyeballing computed styles: the submit button carries
`transition: background-color 0.2s ease`, so `getComputedStyle` immediately after toggling
`:disabled` returns the color it is transitioning *from*. Wait out the transition or the
derived shade looks like it is not applying when it is.
