# Inlined fonts

Design notes for `_includes/styles/inline-fonts.scss`, `assets/css/fonts.scss` and the
three faces the site ships. See also [early-hints.md](early-hints.md), which removes the
cold-start round trip this arrangement costs, and [swashes.md](swashes.md) for how Sunday
Club's coverage and features are built.

Rebuild commands:

```bash
bin/font-features.py            # Sunday Club: full build
bin/font-features.py --report   # show the derived rules, write nothing
bin/font-audit.py               # shape a word list and check for colliding swashes

bin/subset-sourcesans.py            # Source Sans Pro Light: rebuild
bin/subset-sourcesans.py --report   # measure, write nothing
```

`_includes/styles/inline-fonts.scss` carries three faces as base64, so text paints without
a font request. That is 87% of a typical page's compressed weight, which makes these the
only assets on the site where a wasted kilobyte is worth chasing.

They are *base64 in a stylesheet*, but that stylesheet is no longer inlined into the HTML.
`assets/css/fonts.scss` builds it to `/assets/css/fonts.css` and `_layouts/default.html`
links it render-blocking as the first element in `<head>`. See "Why a separate file"
below for the measurements; the short version is that inlining made every page view
re-download 40KB the visitor already had.

**The href carries no cache-buster, and must not grow one.** It is a bare
`/assets/css/fonts.css`, because Cloudflare replays a *static* `Link` header for it as a
103 Early Hint (see [early-hints.md](early-hints.md)) and a dashboard rule cannot read a
build-time digest. A `?v=` that drifts from that hardcoded header costs a double download.
Freshness is handled at the edge instead, by `stale-while-revalidate` on the response.

This replaced a `FontCacheKey` generator that stamped `?v=<digest>` onto the href. If the
Early Hints rules are ever removed, that is the scheme to restore -- hash the *inputs*
(`inline-fonts.scss` plus `_includes/fonts/*.b64`) rather than the rendered output, since
the layout needs the value while rendering, before any page output exists to hash.

Note the `.ttf` fallback `url()`s in `inline-fonts.scss` are **root-relative**. They used
to be `../assets/...`, which resolved against the HTML document; from
`/assets/css/fonts.css` that same string resolves to `/assets/assets/...` and 404s.

Base64 is close to free once brotli has run -- the inflation is about 1% against the raw
woff2 -- so the cost is the *font*, not the encoding. Both inlined text faces are built by
a script from a pristine vendor source, never from the previous output, since subsetting an
already-subset font ratchets its coverage down a little on every run:

| face | source of truth | built by |
| --- | --- | --- |
| Sunday Club Bold | `assets/fonts/SundayClub-Bold.woff` | `bin/font-features.py` |
| Source Sans Pro Light | `assets/fonts/SourceSansPro-Light.vendor.woff2` | `bin/subset-sourcesans.py` |
| SFSymbols (icons) | `assets/fonts/SFSymbols/` | hand-built, 5 glyphs, already minimal |

Source Sans Pro's vendor build shipped a `GPOS` three times the size of its outlines --
42.6KB against 14.1KB of `glyf` -- holding the `size` feature, which is an optical-size
record no browser consults, and kern pairs for glyphs the subset does not contain. Pruning
`GPOS` to the shipped glyphs takes it to 4.8KB and the file from 14.5KB to 9.1KB. Kerning is
kept, and so is hinting: 1.9KB for legibility at the site's 20px base on Windows. The script
fails the build if coverage regresses against the vendor file, and pins `head.modified` so an
unchanged rebuild does not churn the base64 blob in git.

## Why a separate file, and what it costs

Moving the faces out of the HTML trades one round trip on a visitor's *first* page for
40KB on every page after it. Measured on the built site over brotli, with production cache
headers (`max-age=600` HTML, `max-age=172800` assets), median FCP of 7-9 runs:

| profile | cold (first page) | warm (next page) | warm transfer |
| --- | --- | --- | --- |
| Fast 4G (85ms/9Mbps) | 176 -> 268ms (+92) | 180 -> 140ms (-40) | 48.9KB -> 8.6KB |
| Slow 4G (150ms/1.6Mbps) | 428 -> 580ms (+152) | 412 -> 228ms (-184) | 48.9KB -> 8.6KB |
| 3G (300ms/750Kbps) | 836 -> 1120ms (+284) | 820 -> 404ms (-416) | 48.9KB -> 8.6KB |

The cold penalty is exactly one RTT and nothing more -- it is the request itself, not the
bytes, since the payload is unchanged (45,573 -> 45,607 bytes total). Break-even is two
pages per session, and the warm saving grows as the connection gets worse while the cold
penalty does not. Real-world cold is milder than this table: Cloudflare serves the site
with `cf-cache-status: DYNAMIC` on HTML, so the document costs a full trip to the GitHub
origin (TTFB 310-540ms measured) while `fonts.css` is edge-cacheable (~110ms).

That cold RTT is what the Early Hints setup removes; see
[early-hints.md](early-hints.md).

**This does not change what paints.** A `<link rel=stylesheet>` in `<head>` is
render-blocking, so the `@font-face` rules are in the CSSOM before first paint; the faces
are `data:` URLs, so there is no second fetch to wait on. Verified by CDP screencast on
`/`, `/resume`, `/portfolio` and a post: FCP lands 40-60ms after `fonts.css` finishes, and
the first frame containing any text is pixel-identical to the fully-loaded render -- byte
for byte the same as the inline build's first text frame. No frame ever paints a fallback
face. Both builds do show one earlier frame with layout but no glyphs, which is
`font-display: block` working as intended and is not new.

Keep `stylish.scss` inline. It is 4.5KB, it changes far more often than the fonts, and
folding it into `fonts.css` would bust the font cache on every style tweak.

## font-display, and why there are no fallback @font-face rules

Serving the faces as `data:` URLs removes the *font* fetch, but not the two-pass layout.
Chrome routes even a `data:` URL through its remote-font pipeline: it lays the page out once
using whatever local face the stack names, finishes decoding the webfont about 12ms later,
and lays out again. Both passes happen before first paint here -- fonts land around 53ms,
FCP is at 97ms -- so no user sees a flash or a jump.

All three faces use `font-display: block` rather than `swap`. There is no network to wait
on, so the block period costs nothing measurable (FCP/LCP are unchanged at 0.9s/1.2s), and
it makes "the real face is the one that paints" a guarantee instead of a race. `swap`
renders immediately in a local face and reflows on arrival; `optional` is worse than
either, since a miss pins the whole load to the fallback.

**Do not add metric-matched fallback `@font-face` rules (`size-adjust`, `ascent-override`
…) to go with this.** It was built, measured and reverted. Because `block` means the
fallback is never painted, matching its metrics only changes the geometry of a layout
nobody ever sees. It cost 146 bytes brotli'd on every page view and bought a human nothing.
This changes if the faces ever stop being inlined -- over the network the block period can
genuinely expire, the fallback really paints, and metric matching becomes a user-facing fix.

### Reading a CLS number here

Worth knowing before chasing one. Lighthouse derives CLS from `LayoutShift` **trace**
events, which include pre-paint ones; the `layout-shift` PerformanceObserver -- what field
and CrUX CLS are built from -- correctly ignores them. Instrumented both on the same loads:
the observer reported 0 on 8 of 8, while trace events fired on 5 of 8 at 0.183, every one
of them before FCP. So a page can read 0.186 in the lab with a perfectly clean field score,
and since ranking uses CrUX rather than Lighthouse, a lab-only CLS number is not worth
spending bytes on.

It is also a race, so the same build scores 0 on one run and 0.186 on the next with no
change in between. Never conclude a fix worked from a single run; take the worst of six.
There is no lighthouse CLI installed -- use `npx lighthouse@13` with `CHROME_PATH` pointed
at system Chrome, and note the playwright browsers are not installed either, so scripted
runs need `chromium.launch({ channel: 'chrome' })`.

The remaining CLS on `/portfolio` and `/kindag` is *not* fonts -- it is lazy-loaded images
with no intrinsic size, which is a separate fix.

Sunday Club's coverage is set by `SUBSET_RANGES` in `bin/font-features.py`, and it is the
expensive knob on this site: every base glyph drags in up to seven swash variants *and* the
`calt` rules that place them, so a codepoint costs several times what it would in a text
face. It is scoped to what headings actually use.
