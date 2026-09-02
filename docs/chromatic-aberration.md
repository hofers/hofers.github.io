# Chromatic aberration (`_includes/styles/_sass/_aberration.scss`)

Design notes for the `.aberrate`, `.aberrate--hover` and `.aberrate--wander` classes. The stylesheet carries only
what you need to edit it safely; this file is the record of why it is shaped that way, and
of the things that were tried and rejected.

## What it does

Splits the text into red, green and blue layers and displaces the outer two, the way a lens
does. RGB is additive, so on a dark ground the three layers must *sum* to the text color --
that is the whole constraint, and `ca-layer()` enforces it. Whatever `$ca-strength` is set
to, the overlap stays exactly the text color and only the fringes change.

The same effect on a light ground would be the subtractive dual: cyan/magenta/yellow inks
under `multiply`, each taking one channel out of the white behind the glyph. Not built.

### Three layers, not two

Two layers would put a red fringe on one side and a blue one on the other and leave the text
itself alone -- simpler, and steadier at small sizes. But the middle layer is what produces
the yellow, cyan and magenta bands where pairs of layers overlap, and those bands are most
of the effect.

### Derived from `currentColor`, not from a compiled color

Not a convenience, a correctness condition. An `h1` is `$colorHeadingPrimary`, a subtitle
`h2` is `$colorHeadingSecondary`, and a portfolio item's title is a `$colorHeadingPrimary`
link *inside* an `h2` -- three different colors, and a layer set that sums to the wrong one
silently recolors the heading. (The `h2` rule this replaced left portfolio titles about 10%
dim.) It also means the effect follows a color that changes under it, a link's `:hover`
among them, with no rule of its own.

### Not an SVG filter

A filter rasterises its input and caches the result; iOS Safari re-uses that cache when you
pinch-zoom rather than re-rendering from the outlines, so the text goes soft and stays soft.
Painting three real text layers keeps glyphs as glyphs at every scale.

Desktop Chrome renders the filter and this pixel-identically -- verified at DPR 1 and 2,
under zoom, transform and page-scale -- so the regression this avoids is not reproducible in
a desktop lab.

### Why headings only

`plus-lighter` sums *alpha* as well as color, so three copies of a partially-covered edge
pixel accumulate to three times the coverage and antialiased edges composite too dark. On a
100px display face the strokes are solid and it is invisible. On 20px body text most of the
stroke *is* edge, and the text renders visibly thin and tinted toward green. Hence the
always-on class for headings and the hover variant for anything at body size.

## Why the base layer is painted with `-webkit-text-fill-color`

`color: rgb(from currentColor ...)` does work -- inside the `color` property itself
`currentColor` means the *inherited* color, so it is not circular, and it is the obvious way
to write this. The trouble is what it leaves behind: the element's computed `color` would
then hold the green third, which is what the two pseudo layers inherit and would have to
scale back up to recover the original.

The hover variant cannot afford that, because there the base color is mid-transition for
180ms: the fringes would be derived from a moving origin through a ~6.6x channel gain, clip,
and flare white on the way in. Painting the base layer as a *fill* leaves `color` holding the
real text color, so all three layers read one unchanging origin and the sum holds at every
point of the transition. It keeps text-decoration and every other `currentColor` consumer on
the true color too, rather than on a third of it.

## The `@supports` gate on the pseudo layers

Relative color syntax is the hard requirement (Chrome 119, Safari 16.4, Firefox 128), and
its absence is not benign: every `color(from ...)` would be dropped, the pseudo layers would
paint the *full* text color, and three of those under `plus-lighter` blow out to white. So
the copies are gated on `@supports` and simply never materialise. A browser that old renders
the heading as ordinary text, which is the right failure.

## The blending color space, and the branch that picks one

`plus-lighter` adds whatever numbers the compositor is holding, and that is not the same
thing everywhere. Measured by sampling the triple overlap of a solid block beside a swatch of
the target color, for the h2 color `#e2e9ea` (226 233 234):

| engine                     | composites in             | split in sRGB  | split in P3    |
| ---                        | ---                       | ---            | ---            |
| Chrome macOS, P3 display   | Display P3, encoded       | 255 247 255    | 226 233 233 ok |
| Chrome macOS, sRGB display | sRGB, layers gamut-mapped | 226 233 234 ok | 216 209 197    |
| Safari macOS               | Display P3, encoded       | 255 246 255    | 227 232 233 ok |
| Safari iOS                 | extended sRGB, unclamped  | 227 232 234 ok | 133 190 154    |

So the layers are split in the space the compositor will add them in: `--ca-space`, srgb by
default, display-p3 wherever the compositor is the desktop one on a wide-gamut display. The
layers are all derived through one custom property so that branch is a single declaration
rather than a second copy of every layer.

The sRGB-split error on a P3 compositor is a magenta lift, about 13% in red: the two
channels a layer does *not* own convert upward into P3 by more than the owned one converts
down, and three layers accumulate that three times over. It shows on h2 and not h1 for a
dull reason -- `#fbfeff`'s layers overflow and clip to white, which is about where they were
headed anyway, while `#e2e9ea`'s land just past the top of red and blue.

### Chrome changed sides, and that is the lesson

The first two rows used to be one row. Chrome composited in sRGB on the very Mac where Safari
did not, and the branch was gated on a WebKit-only feature query for exactly that reason. As
of Chrome 152 (measured on macOS 26.7, P3 display) it composites in the display's space like
every other app on the machine, and the sRGB split it used to need now blows the h2 out to
255 247 255 -- within a point of the number macOS Safari produced from the same mistake, which
is how you can tell it is the same mistake and not a new one. The h1 `#fbfeff` clips to a flat
255 255 255.

The branch is no longer gated on the engine, because the engine was never what determined the
answer -- the platform's compositor was, and engines migrate onto it. What the conditions now
describe is a machine, not a browser: a desktop-class compositor and a wide-gamut display,
minus iOS. Anything that ships a color-managed compositor on a P3 display lands on the P3
side by default, which is the direction the whole ecosystem has been moving.

### Why the gate is shaped the way it is

The two failure directions are not symmetric, and that is what the conditions are for. Being
wrong on a desktop costs a cast: the 13% magenta lift going one way, the dull 216 209 197
going the other. The first of those shipped for months before anyone noticed, and is the
better guide to how loud either is. Gaining the branch on iOS drops the heading to
133 190 154 -- a pale green, against a target of 226 233 234. Converting a P3 layer to sRGB
primaries sends two of its three channels negative
(the green layer is -84 182 -42), extended sRGB keeps the negatives rather than clamping them,
and the three layers partly cancel instead of adding. All of these are measurements, one taken
by shipping it to a phone.

So the only thing worth spending conditions on is keeping iOS out, and it is excluded twice
over, by two independent facts. The branch needs both:

- `not (-webkit-touch-callout: none)`. The property is iOS-family WebKit only: measured true
  on an iPhone, false on macOS Safari and false in Chrome 152, and it is those second two
  halves that would be dangerous to assume. Verified rather than assumed for Chrome, because
  the whole branch now hangs on it -- a Chromium that supported the property would silently
  switch the P3 split back off.
- `(hover: hover) and (pointer: fine)`, false on the same iPhone. It also catches an iPad
  running with a trackpad, where touch-callout is true but the compositor is iOS's.

`(color-gamut: p3)` is the display half, since a machine on an sRGB display composites in sRGB
and reports the narrower gamut from the same profile that decides it.

What is deliberately *not* in the gate any more is an engine test. `-webkit-named-image` used
to be there, as the WebKit half -- a real feature no Chromium had, not a version sniff. It was
an honest reading of the measurements at the time and it still went stale the moment Chrome's
compositor moved, in the direction that produces the loudest error. A detector for the other
side was considered and rejected: `paint()`, the obvious Chromium-only feature, reports
unsupported in Chrome 152 (`CSS.supports('background: paint(id)')` is false), and the
remaining candidates are all one release away from the same fate. Naming engines is what
failed; the gate describes the hardware instead.

### What is measured and what is inferred

Measured, on macOS 26.7 with a P3 display: Safari 27 and Chrome 152 both need the P3 split.
Measured on an iPhone: iOS Safari needs sRGB. Everything else the gate now admits -- Firefox
anywhere, Chromium on Windows or Linux driving a wide-gamut monitor -- is an inference from
"the platform compositor decides", not a reading.

That is a deliberate bet in the milder direction. If one of those turns out to composite in
sRGB after all, it gets 216 209 197: a heading about 7% dim and slightly warm, the error that
went unnoticed for months. The reverse default would give it 255 247 255, the blown magenta
that got noticed within a day. When the space is unknown, P3 is the cheaper thing to be wrong
about.

To check one of them, load a heading on that machine, screenshot it, and sample the solid core
of a glyph: it should read the heading color (`#fbfeff` on an h1, `#e2e9ea` on an h2) to
within a point or two. Sample the core, not an edge -- the fringes are supposed to differ.

## The bleed, and why it is a shadow

Safari clips each blended layer to its paint bounds, and glyph ink leaves that box all the
time. The layer box is the element's, which is a stack of line boxes; anything outside it --
a Sunday Club swash reaching back under the letter before it, a descender under this site's
tight display line-heights -- is cut off at a hard vertical or horizontal edge. Chrome paints
the same markup uncut, which is why this survived to a phone: it does not reproduce in a
Chromium lab at any width, zoom or DPR.

`--ca-bleed` fixes it by widening the layer's paint bounds with a transparent spread shadow.
Three properties do that, and the difference between them is the whole point:

| how                                          | fixes the clip | cost                                        |
| ---                                          | ---            | ---                                         |
| `inset: -1em` + `border: 1em` transparent    | yes            | a real box: adds scrollable overflow        |
| `outline: 1em solid transparent`             | yes            | forced-colors mode paints it                |
| `box-shadow: 0 0 0 1em transparent`          | yes            | none found                                  |

All three render identically in WebKit -- 0 pixels apart from each other over the h1 -- so
the choice is made entirely on what else they do.

The border version is the honest one, and it is the one to reach for first: it grows the
layer's border box and hands the em back as a transparent border, so `padding: inherit`
still lands the text on the same origin at the same wrapping width. But an absolutely
positioned box contributes to its ancestors' scrollable overflow, and a box an em wider than
a full-bleed heading puts a horizontal scrollbar on the page -- measured at 768px, where the
document went 802px wide, and vertically too. A shadow is paint, not layout: measured across
six widths and eight pages in both engines, `scrollWidth` and `scrollHeight` are unchanged.

`outline` has the same property and is the more idiomatic "paint outside the box", but in
forced-colors mode `outline-color` is forced to a system color, and a 1em transparent
outline would become a 1em visible ring around every heading. `box-shadow` is forced to
`none` there instead, which degrades to the Safari clip -- the bug, not a new one.

An em is not measured from the headings that ship. Glyph ink is drawn inside the em square,
the box is already at least a line box tall, and the shadow costs nothing that would reward
tuning it down, so the value is set past what any face can use rather than to what this
site's faces do use. Raise it per element via `--ca-bleed` if some future face proves that
wrong.

Both the shadow and the transparent color are load-bearing. `plus-lighter` sums what it is
given, and transparent sums to nothing, so the shadow is invisible in the blend -- verified
pixel-identical to Chrome's uncut rendering. A shadow with a color would paint a slab of it
under all three layers.

## Displacement is a product, and each variant supplies one factor

```
displacement = --ca-shift * --ca-gate * --ca-wander-x     (and the same on the other axis)
                 authored     0..1        -1..1
                 amplitude    --hover     --wander
```

`.aberrate` writes that line once. `--ca-gate` and the two wander numbers are registered with
an initial value of `1`, so plain `.aberrate` declares neither and no variant has to out-
specify another to have its say: `--hover` closes the gate, `--wander` moves the path, and
`hover wander` is both -- a walk that only runs while the pointer is on the element. That
combination is what the footer icons use.

This is not how it was first written. Each variant used to write `--ca-active-shift` itself,
which meant the two could not be combined at all: they set the same property at the same
specificity, so one won on source order and the filter warned rather than shipping whichever
that was. Multiplying instead of overwriting is what makes them compose, and it is worth
keeping that way -- a third variant should be a third factor.

Two consequences worth knowing:

- **The rest state of a gated variant is a product, not a literal.** It computes to `0px`
  because it is `0.05em * 0 * 0.38`, a calculation that keeps its unit. See the note in "One
  animation" about what a bare `0` used to do here.
- **An inline `--ca-shift` from the filter scales whatever the variants are doing**, because
  it is the first factor and lands in a style attribute. `{{ x | aberrate: "hover wander
  0.03em" }}` narrows the walk without touching the gate.

## The hover variant

At rest this is not a dimmed version of the effect, it is ordinary text: the layers are faded
out and the element paints its own color rather than the green third of it. That matters
because at zero displacement the three layers still paint, and three coincident copies land
straight on the alpha problem above -- which is the state a link spends nearly all of its
life in. Measured against untouched text at the same glyph origin, the rest state differs by
0 pixels of 8500.

`--ca-gate` is the only factor this variant touches, and closing it multiplies the
displacement to zero rather than replacing it -- which is what leaves the wander factor free
to keep moving underneath.

The two halves swap in step on hover: the text goes from its full color to the green layer
while the other two fade from nothing to full. Because the three sum to the text color, and
both halves run on the same duration and easing, the total stays that color at every point
in between -- the text separates without ever changing brightness. This is the invariant that
requires the fringes to be fixed to `color` rather than derived from the fill that is
animating.

### One animation, not four

The obvious way to write the transition is the way this started: each layer transitions its
own `transform` and its own `opacity`, and the element transitions its fill. That is four
animations of the same 180ms, and nothing but the engine's good manners keeps them together.
Safari's manners were not good -- for roughly the first tenth of a second of every hover the
red layer stood further out than the blue one, then the two settled. On a footer icon, where
the whole glyph is one shape, it reads as a flinch.

The same staggering broke the color invariant, and that one had a name before it had a
cause: a green flash on hover. The fill moves from the text color to the green third and the
other two layers fade in to make the difference up; the sum only holds if those halves are
exactly in step. When the fill got there first there was nothing yet adding red and blue back,
so the glyph showed the green third of its color until the layers caught up.

Two separate things were wrong, and the first is worth knowing about on its own:

- The rest value was `0`, unitless, and `::before` *negates* it. `translate()` takes a
  `<length-percentage>` and `calc(0 * -1)` is a number, so `::before`'s whole `transform`
  declaration was invalid at computed-value time and fell back to `none`, while `::after`,
  which uses the variable directly, kept a valid `translate(0, 0)`. Both engines report
  exactly that: `none` against `matrix(1, 0, 0, 1, 0, 0)`. The layers sit in the same place
  either way, so nothing looks wrong at rest -- but the two then *start* the transition from
  different kinds of value, `::after` matrix to matrix and `::before` out of `none`, which is
  a different code path. The gate retired the hazard rather than fixing it: the rest value is
  now `--ca-shift * 0 * ...`, and a calculation over a length stays a length. Do not
  "simplify" a variant back to writing a bare `0` into `--ca-active-shift`.
- That alone did not fix it, because four animations can drift apart for reasons that are not
  in the stylesheet at all -- when each layer gets promoted to a composited layer, how a
  blended layer is scheduled.

So the layers no longer animate. The *element* transitions `--ca-gate` and
`--ca-active-alpha` alongside its fill, and the layers read them and paint: position from the
gate through the product above, `opacity` from the alpha, no `transition` of their own. There
is now one clock. Two layers cannot come apart when neither is animating -- the mirroring is
arithmetic, done fresh from a single interpolated number every frame.

Both axes hang off that one number, so this is three transitions rather than four, and the
displacement is not among them: `--ca-active-shift` and `--ca-active-drift` are recomputed
from the gate, never interpolated. They stay registered for their *type* -- a registered
length that goes bad falls back to the `0px` initial value, where an unregistered one would
invalidate the layer's whole `transform` declaration.

`@property` needs Safari 16.4, Chrome 85, Firefox 128; relative color syntax, which the
layers are already gated on, needs Safari 16.4, Chrome 119, Firefox 128. The second is the
stricter requirement in every engine, so anything that has the layers at all can animate them
and no new `@supports` is needed.

The cost is that a transition driving `transform` through a custom property is recomputed in
style rather than run on the compositor. For a heading or an icon that is nothing, and it is
the same property that removes the promotion race.

Verified in both engines: sampled every frame of the hover, the two transforms are exact
mirrors at every sample and the opacities equal; the rest state is 0 pixels of 95400 from the
layers switched off entirely, and the settled hover state 0 pixels from the same values
applied statically with no transition at all.

The state selectors are descendant (`a:hover &`) rather than child, because a footer icon's
wrapper sits inside the `<i>`, not directly under the `<a>`. `:focus-visible` carries the
effect to the keyboard, where a hover-only effect is otherwise invisible.

## The wander variant

`.aberrate--wander` is the effect with both displacements in continuous motion, so the glyph
reads as a lens hunting for focus rather than a lens stuck out of it.

Nothing about the layers changes. Displacement still comes from one number per axis, the
layers are still exact mirrors of it, and the three still sum to the text color at every
frame -- the only difference from `.aberrate` is that the two numbers move.

### Numbers in the keyframes, not lengths

The walk is authored as a plain number in `-1..1` in `--ca-wander-x` / `--ca-wander-y`, and
multiplied by `--ca-shift` / `--ca-drift` in an ordinary declaration:

```scss
--ca-active-shift: calc(var(--ca-shift) * var(--ca-gate) * var(--ca-wander-x));
```

Two reasons, and the second is the load-bearing one:

- The amplitude stays a single authored length. `{{ x | aberrate: "wander 0.03em" }}` writes
  an inline `--ca-shift` and narrows the whole walk, exactly as it narrows the static
  separation in the other two variants. Lengths in the keyframes would have made the
  filter's length option silently do nothing here.
- A keyframe value containing `var()` has to be substituted before it can be interpolated,
  and that is thin ice across engines. Literal numbers in the keyframes and the `calc()` in
  a normal declaration is the boring path: the animation interpolates a bare number, and the
  length falls out of a var substitution that happens the same way it does everywhere else.

`--ca-wander-x` and `--ca-wander-y` are registered `inherits: false`. They are read on the
element itself; `--ca-active-shift`, computed from them, is what inherits down to the layers.

Registration matters for a second reason: keyframes cannot *interpolate* an unregistered
custom property, they step between stops. So without `@property` the walk would be a stutter
rather than a drift. That needs Safari 16.4 / Chrome 85 / Firefox 128, and the layers are
already gated on relative color syntax, which is stricter in every engine -- anything that
has layers at all can animate them smoothly, and no new `@supports` is needed.

### What makes it look random

Nothing here is random; CSS has no source of randomness that is safe to ship yet. Three
cheap things stand in for it, and they matter in this order:

- **Two clocks, not one.** The axes run separate animations at 5.3s and 4.1s. Each is
  periodic, but the pair only returns to the same phase after their least common multiple,
  which is minutes rather than seconds -- 3.6 of them here. Round these to 5s and 4s and the
  figure closes every 20s and starts to read as a loop.
- **Unevenly spaced stops.** Ten stops at irregular percentages with `ease-in-out` between
  them gives the path changes of pace. Evenly spaced stops read as a rhythm no matter what
  the values are, which is the one thing this must not do.
- **A per-element offset.** `--ca-wander-offset` is an `animation-delay`, negative so the
  element starts part-way along the path instead of ramping in from its first keyframe. The
  second clock takes `1.7x` the same offset; giving both the same delay would slide the pair
  along together and leave every element in the same relative phase. `stylish.scss` sets
  four offsets on the footer, because five icons in a row moving in step read as one object
  rather than five.

The first and last stop of each keyframe set are the same value, so the loop does not jump.

### Under `prefers-reduced-motion`

The animation is dropped and the two numbers are pinned at `0.4` and `0.2`, which through
the same multiply is exactly `.aberrate`'s static `0.02em` / `0.01em`. Deliberately not
zero: at zero the three layers are coincident, and three coincident copies under
`plus-lighter` are the alpha problem in "Why headings only". Reduced motion should take the
motion away, not the effect.

Combined with `--hover` the same pinning applies on top of that variant's `transition: none`,
so a hovered icon is `.aberrate`'s static split, arrived at instantly.

### Combined with `--hover`

`hover wander` is what the footer icons use: at rest they are ordinary single-color icons,
and the walk runs only while the pointer (or keyboard focus) is on one. The two rules already
compose through the product -- one closes the gate, the other moves the path -- so the
combined rule adds only two things:

- **The amplitude.** Both variants set `--ca-shift`, at the same specificity, so on an
  element carrying both it would be settled by which one is written later in the file. The
  combined rule states it, from the same `$ca-wander-amplitude` the standalone variant uses.
- **`animation-play-state: paused`, running only when open.** Nothing is visible at rest, so
  there is no reason to restyle two layers every frame until the pointer arrives -- and this
  is the variant that goes on a whole row of icons. Paused rather than stopped, so the walk
  resumes where the last hover left it instead of retracing the same opening from keyframe
  zero every time; the per-element offsets still hold the row apart.

The gate transition and the walk are independent clocks and are meant to be. Sampled every
frame of a hover: the gate runs 0 to 1 over the 180ms in `ease-out` while the wander numbers
carry on moving underneath, and the layers are exact mirrors at every sample throughout.

Leaving the pointer pauses the walk immediately and the gate closes over 180ms, so the layers
retract along a frozen path rather than continuing to wander on the way out.

### The cost

A custom property driving `transform` is recomputed in style rather than run on the
compositor -- the same trade the hover variant makes, and there for the same reason. The
difference is that a standalone wander never stops: every element carrying one restyles
itself and its two layers every frame for as long as the page is open. Combined with
`--hover` that cost is only paid while something is hovered, which is most of why the footer
uses the pair. Either way this is a variant to opt into on a handful of glyphs, not something
to put on a page of headings.

## Smaller decisions worth not re-deriving

- **`display: inline-block`** -- the layers are absolutely positioned against this box, and
  an inline span split across two lines has fragment geometry `inset: 0` cannot follow. The
  box still wraps internally, and the layers re-wrap identically since they inherit the same
  width, font and features.
- **`isolation: isolate`** -- blend the layers with each other, never with the page behind.
- **`--ca-drift`** -- without vertical drift the horizontal strokes get no fringe at all; the
  channels stay perfectly stacked there and it reads as print misregistration, not a lens.
  `.aberrate` runs half the horizontal shift (`0.02em` / `0.01em`), which is enough at display
  sizes; `.aberrate--hover` overrides both to `0.02em`, because at body size the smaller drift
  is invisible and the effect only has to read for the moment the pointer is over the link.
- **`--ca-active-shift` / `--ca-active-drift`** -- the product the layers read, written once
  in `.aberrate` so that a variant contributes a factor rather than a value. Registered for
  their type, not for interpolation; the thing that interpolates is `--ca-gate`. See
  "Displacement is a product".
- **`content: attr(data-text) / ""`** -- the `/ ""` is alt text, and stops screen readers
  announcing the duplicated string. The element's own text is the green layer, so there is no
  extra text node and the accessible name stays single.
- **`text-shadow: none`** -- a glow underneath three stacked copies reads as mud.
- **`font-feature-settings` is inherited**, so all three layers shape identically and the
  contextual swashes line up. A mismatch would misregister every alternate glyph.
- **`$ca-share` is rounded before `$ca-own` is derived from it**, so the three scales sum to
  exactly 1 and the core of the glyph keeps the text color to the bit.
