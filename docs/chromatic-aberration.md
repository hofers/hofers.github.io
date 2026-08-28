# Chromatic aberration (`_includes/styles/_sass/_aberration.scss`)

Design notes for the `.aberrate` / `.aberrate--hover` classes. The stylesheet carries only
what you need to edit it safely; this file is the record of why it is shaped that way, and
of the things that were tried and rejected.

## What it does

Splits the text into red, green and blue layers and displaces the outer two, the way a lens
does. RGB is additive, so on a dark ground the three layers must *sum* to the text colour --
that is the whole constraint, and `ca-layer()` enforces it. Whatever `$ca-strength` is set
to, the overlap stays exactly the text colour and only the fringes change.

The same effect on a light ground would be the subtractive dual: cyan/magenta/yellow inks
under `multiply`, each taking one channel out of the white behind the glyph. Not built.

### Three layers, not two

Two layers would put a red fringe on one side and a blue one on the other and leave the text
itself alone -- simpler, and steadier at small sizes. But the middle layer is what produces
the yellow, cyan and magenta bands where pairs of layers overlap, and those bands are most
of the effect.

### Derived from `currentColor`, not from a compiled colour

Not a convenience, a correctness condition. An `h1` is `$colorHeadingPrimary`, a subtitle
`h2` is `$colorHeadingSecondary`, and a portfolio item's title is a `$colorHeadingPrimary`
link *inside* an `h2` -- three different colours, and a layer set that sums to the wrong one
silently recolours the heading. (The `h2` rule this replaced left portfolio titles about 10%
dim.) It also means the effect follows a colour that changes under it, a link's `:hover`
among them, with no rule of its own.

### Not an SVG filter

A filter rasterises its input and caches the result; iOS Safari re-uses that cache when you
pinch-zoom rather than re-rendering from the outlines, so the text goes soft and stays soft.
Painting three real text layers keeps glyphs as glyphs at every scale.

Desktop Chrome renders the filter and this pixel-identically -- verified at DPR 1 and 2,
under zoom, transform and page-scale -- so the regression this avoids is not reproducible in
a desktop lab.

### Why headings only

`plus-lighter` sums *alpha* as well as colour, so three copies of a partially-covered edge
pixel accumulate to three times the coverage and antialiased edges composite too dark. On a
100px display face the strokes are solid and it is invisible. On 20px body text most of the
stroke *is* edge, and the text renders visibly thin and tinted toward green. Hence the
always-on class for headings and the hover variant for anything at body size.

## Why the base layer is painted with `-webkit-text-fill-color`

`color: rgb(from currentColor ...)` does work -- inside the `color` property itself
`currentColor` means the *inherited* colour, so it is not circular, and it is the obvious way
to write this. The trouble is what it leaves behind: the element's computed `color` would
then hold the green third, which is what the two pseudo layers inherit and would have to
scale back up to recover the original.

The hover variant cannot afford that, because there the base colour is mid-transition for
180ms: the fringes would be derived from a moving origin through a ~6.6x channel gain, clip,
and flare white on the way in. Painting the base layer as a *fill* leaves `color` holding the
real text colour, so all three layers read one unchanging origin and the sum holds at every
point of the transition. It keeps text-decoration and every other `currentColor` consumer on
the true colour too, rather than on a third of it.

## The `@supports` gate on the pseudo layers

Relative colour syntax is the hard requirement (Chrome 119, Safari 16.4, Firefox 128), and
its absence is not benign: every `color(from ...)` would be dropped, the pseudo layers would
paint the *full* text colour, and three of those under `plus-lighter` blow out to white. So
the copies are gated on `@supports` and simply never materialise. A browser that old renders
the heading as ordinary text, which is the right failure.

## The blending colour space, and the branch that picks one

`plus-lighter` adds whatever numbers the compositor is holding, and the three engines hold
three different things. Measured by sampling the triple overlap of a solid block beside a
swatch of the target colour, for the h2 colour `#e2e9ea` (226 233 234):

| engine       | composites in             | split in sRGB  | split in P3    |
| ---          | ---                       | ---            | ---            |
| Chrome       | sRGB, layers gamut-mapped | 226 233 234 ok | 216 209 197    |
| Safari macOS | Display P3, encoded       | 255 246 255    | 227 232 233 ok |
| Safari iOS   | extended sRGB, unclamped  | 227 232 234 ok | 133 190 154    |

So the layers are split in the space the compositor will add them in: `--ca-space`, srgb by
default, display-p3 only where the compositor is macOS's. The layers are all derived through
one custom property so that branch is a single declaration rather than a second copy of every
layer.

The macOS Safari error is a magenta lift, about 13% in red: the two channels a layer does
*not* own convert upward into P3 by more than the owned one converts down, and three layers
accumulate that three times over. It shows on h2 and not h1 for a dull reason -- `#fbfeff`'s
layers overflow and clip to white, which is about where they were headed anyway, while
`#e2e9ea`'s land just past the top of red and blue.

### Why the gate is shaped the way it is

The two failure directions are not symmetric, and that is what the conditions are for. Losing
the branch on macOS costs the 13% lift, which is what shipped for months before anyone
noticed. Gaining it on iOS drops the heading to 133 190 154 -- a pale green, against a target
of 226 233 234. Converting a P3 layer to sRGB primaries sends two of its three channels
negative (the green layer is -84 182 -42), extended sRGB keeps the negatives rather than
clamping them, and the three layers partly cancel instead of adding. Both numbers above are
measurements, one taken by shipping it to a phone.

So iOS is excluded twice over, by two independent facts, and the branch needs both:

- `-webkit-touch-callout` is iOS-family WebKit only: measured true on an iPhone and false on
  macOS Safari, and it is that second half that would be dangerous to assume.
- `(hover: hover) and (pointer: fine)`, false on the same iPhone. It also catches an iPad
  running with a trackpad, where touch-callout is true but the compositor is iOS's.

`-webkit-named-image` is the WebKit half -- a real feature no Chromium has, not a version
sniff -- and `(color-gamut: p3)` is the display half, since a Mac on an sRGB display
composites in sRGB and reports the narrower gamut from the same profile that decides it. If
an engine ever changes sides, the branch fails toward the 13% lift on desktop rather than
toward green text on a phone.

## The hover variant

At rest this is not a dimmed version of the effect, it is ordinary text: the layers are faded
out and the element paints its own colour rather than the green third of it. That matters
because at zero displacement the three layers still paint, and three coincident copies land
straight on the alpha problem above -- which is the state a link spends nearly all of its
life in. Measured against untouched text at the same glyph origin, the rest state differs by
0 pixels of 8500.

The two halves swap in step on hover: the text goes from its full colour to the green layer
while the other two fade from nothing to full. Because the three sum to the text colour, and
both halves run on the same duration and easing, the total stays that colour at every point
in between -- the text separates without ever changing brightness. This is the invariant that
requires the fringes to be fixed to `color` rather than derived from the fill that is
animating.

The state selectors are descendant (`a:hover &`) rather than child, because a footer icon's
wrapper sits inside the `<i>`, not directly under the `<a>`. `:focus-visible` carries the
effect to the keyboard, where a hover-only effect is otherwise invisible.

## Smaller decisions worth not re-deriving

- **`display: inline-block`** -- the layers are absolutely positioned against this box, and
  an inline span split across two lines has fragment geometry `inset: 0` cannot follow. The
  box still wraps internally, and the layers re-wrap identically since they inherit the same
  width, font and features.
- **`isolation: isolate`** -- blend the layers with each other, never with the page behind.
- **`--ca-drift`** -- without vertical drift the horizontal strokes get no fringe at all; the
  channels stay perfectly stacked there and it reads as print misregistration, not a lens.
- **`--ca-active-shift` / `--ca-active-drift`** -- indirected so the hover variant can gate
  the displacement without having to out-specify an inline `--ca-shift` from the filter.
- **`content: attr(data-text) / ""`** -- the `/ ""` is alt text, and stops screen readers
  announcing the duplicated string. The element's own text is the green layer, so there is no
  extra text node and the accessible name stays single.
- **`text-shadow: none`** -- a glow underneath three stacked copies reads as mud.
- **`font-feature-settings` is inherited**, so all three layers shape identically and the
  contextual swashes line up. A mismatch would misregister every alternate glyph.
- **`$ca-share` is rounded before `$ca-own` is derived from it**, so the three scales sum to
  exactly 1 and the core of the glyph keeps the text colour to the bit.
