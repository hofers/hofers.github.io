# Overbright text (`_includes/styles/_sass/_lift.scss`)

`.lift` paints text past SDR white, so on a display with headroom to spare it reads
brighter than the page's paper white rather than merely being the lightest thing on it.

```markdown
[a lifted link](/somewhere){:.lift}
```

`.lift--hover` is the gated form. `.aberrate--lift` is the same paint wired to the
aberration's own gate; see [chromatic-aberration.md](chromatic-aberration.md).

## The mechanism is the compositor, not an image

The web's *specified* route to brighter-than-white is an ISO 21496-1 gain-map image
painted through `background-clip: text` — a normal SDR JPEG plus a grayscale map saying
how much brighter each pixel may go. It works in Safari 26+ and Chrome 137+, and it is
what [soverybright.com](https://www.soverybright.com/) does.

We do not use it, for a reason that turned out to be structural rather than incidental:
it needs `-webkit-text-fill-color: transparent`, and `.aberrate` already spends that
property on its three-way channel split. One text fill, two claimants. Since the headings
are the whole reason to want this, a route that cannot coexist with them is not a route.

What we use instead is the platform behaviour `docs/color.md` already records for an
unrelated reason: **iOS composites in extended sRGB and does not clamp out-of-range
channels.** A `brightness()` above 1 on a composited element therefore multiplies past
white instead of clipping at it. No image, no gain map, no `background-clip`, no asset
of any kind — the whole feature is one declaration:

```scss
@media (dynamic-range: high) {
  filter: brightness(calc(1 + (var(--lift) - 1) * var(--lift-gate)));
}
```

## What was measured, on an iPhone (iOS 18.7 / Safari 27, `dynamic-range: high`)

Four results, three of which contradict the obvious guess:

- **An out-of-range colour alone does nothing.** `color(from #fbfeff srgb calc(r * 3) …)`
  on plain text paints ordinary white, at any multiplier. Individual paint still clamps;
  only the *composite* escapes. This is the finding that makes `filter` the mechanism and
  rules out doing it in the colour.
- **No HDR content needs to be on the page.** The `filter: brightness(10)` demos that
  popularised this all ship an autoplaying HDR video to put the compositor in extended
  range. Adding and removing a gain-map image from the document changed nothing here.
- **A filter survives an inline line wrap.** A lifted link broken across two lines shows
  no clipping or offset on the second fragment, so `.lift` does not need
  `display: inline-block` and does not change how links wrap.
- **Body copy at 2× is comfortable to read.** The expectation was that this would be
  glare at anything but headline size. It is not, at least on this display.

## One constant, and the ceiling that sets it

`$lift-default` is **1.3**, everywhere — headings, links, nav labels, `.bar`, and
`.aberrate--lift`.

It started at 3, which looked best in isolation on a test page, and came down in use.
There were three constants for a while: flat body-size ink, headings, and aberrated ink
lower again because its fringes are the first thing to degrade once the multiply outruns
the display's headroom. All three converged on 1.3, because the ceiling below binds harder
than any of the reasons to tell them apart.

Split them again if one moves — they were not always the same number, and the reasons for
each are still real. In particular, if display-size headings are ever raised on their own,
aberrated ink has to be held down separately; the selector that did it was
`:is(h1, h2, h3, a):has(.aberrate)`, keyed on carrying an aberrated span rather than on
the tag, so it followed the effect onto footer icons and portfolio links without naming
them.

### The roughness, and why it is not fixable

A glyph's antialiased edge is a partial-coverage blend of text colour and background, so
the multiply amplifies the steps in that ramp along with everything else. The clip at the
display's headroom then compresses the glyph *core* while leaving the *edges* below it:
the core stops getting brighter, the edges keep going, and the letterform reads as furred
rather than bright.

Measured on both iPhone and Mac:

- `brightness(1)` — a filter that is present but multiplies by one — is **clean**.
- `opacity: 0.999`, which composites without a filter, is **clean**.
- Neither `will-change: filter` nor `transform: translateZ(0)` changes anything.

So it is the multiply, not the composited layer. Grayscale antialiasing is *not* the
cause, which rules out the obvious suspect — macOS does drop LCD subpixel antialiasing for
filtered elements, but that is not what is being seen here. The roughness appears between
1.3 and 1.5 and worsens from there.

That threshold is a property of the antialiasing rather than of this site, so it bounds any
future tuning of body-size text no matter how much headroom a display turns out to have.
Display-size ink is the exception: the same edge ramp is a far smaller fraction of a large
glyph, which is why headings tolerate 2.

> **This 1.3 is not the `1 / $ca-own` ceiling** from
> [chromatic-aberration.md](chromatic-aberration.md), which is also 1.30. That one bounds
> a boost applied to the *layer colours* and clips at 1.0. This one is applied after the
> layers have summed, and is bounded by antialiasing and by display headroom. Two things
> sharing a number by coincidence — do not derive either from the other.

It is not load-bearing; `--lift` overrides per use.

## The three invariants

**The `(dynamic-range: high)` gate.** With no headroom the multiply has nowhere to go and
only clips. On `.aberrate--lift` that is actively destructive: it clips each layer to the
same grey that boosting the layer colours produced, so an ungated version would *damage*
the aberration on precisely the displays that cannot show the glow. This is not
progressive-enhancement etiquette; it is the difference between degrading to the base
effect and degrading to a broken one. The declaration is also inside the query rather
than written unconditionally as `brightness(1)`, so a display without headroom is not
handed a composited layer to perform an identity transform on.

**`filter` takes the whole element.** Not just the glyphs — background, border and
box-shadow scale with them. An inline link is safe because its only ink *is* its glyphs
plus a hairline underline, so lifting its box and lifting its text are the same thing. The
nav tabs are not: they paint `background-color` and a `box-shadow` halo, and lifting the
link washed the whole tab out rather than brightening the label. They lift the `<span>`
inside instead, which is already where that link's own ink lives — the active underline
and the hover highlight are both on the span, not the anchor.

Media is the same failure with a photograph instead of a background. `portfolio.md` wraps
each screenshot in a link, and lifting that link brightened the image itself, which reads
as blowing it out rather than as glow. Any link containing `img`, `picture`, `svg`,
`video` or `canvas` therefore opts out of lifting entirely — there is no inner box to
move the paint to, because the text and the media share the anchor.

The general rule: **put the paint on the innermost box that holds only ink you want
lifted, and skip it where no such box exists.** `.bar` is the deliberate exception —
there the background *is* the ink.

Both exclusions are written with `:where()` inside `:not()` and `:has()` so they
contribute no specificity. The link rule has to stay at `(0,0,2)` and lose to
`:is(h1, h2, h3, a):has(.aberrate)` at `(0,1,1)`, or the footer icons silently go back to
3x. Using `:is()` there instead is a one-character change that breaks it quietly.

**Hue holds only under the headroom.** The multiply is uniform, so ratios are preserved
exactly — right up until a channel exceeds what the display can show, at which point that
channel alone is clipped and the ratio breaks. Near-white is the safe case because its
three channels are equal and clip *together*: the glow simply caps out. A saturated colour
clips its strongest channel first and drifts pale. Measured on `--color-teal`, that drift
is visible from 2× and still reads as teal, so treat it as something to look at rather
than a prohibition — but it is why the defaults above were tuned on near-white.

## What it costs, and where it is invisible

`filter` forces the element onto its own composited layer. `.aberrate` is already isolated
and blending so it barely notices; a plain `.lift` on a link is a new layer that would not
otherwise exist.

The effect is Apple-only. It is a compositor property, not a specified behaviour, so
Chrome and Firefox clamp and render the ordinary colour — a clean degradation, and the
reason no fallback is written. It is also absent from screenshots, print and OG cards, all
of which render the SDR composite; at 100% display brightness on macOS, where EDR headroom
goes to zero; and under iOS Low Power Mode. `(dynamic-range: high)` reports that the
display is *capable*, never that headroom exists at this moment, and there is no CSS that
can ask for the latter.

## The rejected route, in case it is revisited

If the gain-map approach is ever wanted for something that is not aberrated — it is the
portable one, and the only one that works in Chrome — two things cost hours:

- **`CGImageSource` reports `kCGImageAuxiliaryDataTypeISOGainMap` for an Adobe-XMP gain
  map too.** It is not a test of anything. The real check is
  `strings f.jpg | grep 21496`: Safari honours only files carrying the
  `urn:iso:std:iso:ts:21496:-1` APP2 marker, in both the primary image and the gain-map
  sub-image.
- **Neither `CIContext.writeJPEGRepresentation` nor `CGImageDestination` will emit ISO for
  JPEG on macOS 26.** `kCGImageDestinationEncodeToISOGainmap` is accepted and silently
  ignored, in image properties and destination options alike; both write Adobe XMP, which
  Safari ignores. Core Image also writes no gain map at all unless the HDR `CIImage`
  carries `settingContentHeadroom()`, and staples a 13 KB RGB ICC profile onto the
  single-channel gain map, which is most of the file size.

The ISO metadata itself is a 61-byte big-endian block whose headroom fields are rational
**log2 stops** — `0x00BA0A7F / 0x00400000` = 2.9066 = 7.5× — appearing twice, as
`alternate_hdr_headroom` and `gain_map_max`.
