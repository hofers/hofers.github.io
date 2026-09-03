# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Overview

This is a Jekyll-based personal professional website for Sean Hofer, hosted on GitHub Pages with
custom GitHub Actions deployment. The site is built with Jekyll 4.3.1 and includes custom plugins
and optimized asset processing.

## Development Commands

### Local Development
```bash
# Install dependencies
bundle install

# Start development server (serves at http://0.0.0.0:4000)
bundle exec jekyll serve
```

### Asset Processing
```bash
# Generate responsive images and WebP conversions
./bin/make-images.sh

# Rebuild Sunday Club's contextual alternates (see docs/swashes.md)
bin/font-features.py            # full build
bin/font-features.py --report   # show the derived rules, write nothing
bin/font-audit.py               # shape a word list and check for colliding swashes

# Re-prune the inlined Source Sans Pro Light (see docs/fonts.md)
bin/subset-sourcesans.py            # rebuild
bin/subset-sourcesans.py --report   # measure, write nothing

```

## Where design rationale goes

Long-form "why" belongs in `docs/<feature>.md`, not in a file header comment. `docs/` is in
`_config.yml`'s `exclude`, so nothing there is published.

A comment is read by someone editing the line beside it, and it should answer one question:
*can I change this, and what breaks if I do.* The record of what was tried, what was measured
and what was rejected has a different reader and belongs in its own document. Folding the
second into the first makes the code unreadable and the rationale unfindable.

So, when a feature needs real explanation:

- **In the file**, a short header -- what it does, the invariant that holds it together, and
  a line pointing at the doc. Roughly a dozen lines, not a screenful.
- **Inline**, one or two sentences on any line someone would otherwise be tempted to
  simplify away, plus the load-bearing warnings ("every one of these conditions matters").
- **In `docs/<feature>.md`**, everything else: alternatives considered and why they lost,
  measurement tables, browser- or platform-specific findings, the failure modes you only
  learn about by shipping.

`docs/chromatic-aberration.md` and `_includes/styles/_sass/_aberration.scss` are the worked
example -- a 103-line header became 13 lines plus a doc.

What is already split out this way: `docs/fonts.md`, `docs/early-hints.md`,
`docs/html-edge-cache.md`, `docs/swashes.md`, `docs/chromatic-aberration.md`,
`docs/color.md`.

## Project Structure

### Core Jekyll Architecture
- `_config.yml` - Main Jekyll configuration with custom plugins and collections
- `_layouts/` - HTML templates (default.html is the main layout)
- `_includes/` - Reusable components and assets
- `_plugins/internal_plugins.rb` - Custom Jekyll plugins and filters
- `_site/` - Generated static site output (excluded from git)

### Collections
- `_portfolio-items/` - Portfolio project entries
- `_press-items/` - Press coverage entries
- `_posts/class/` - Blog posts for class-related content

### Custom Plugins
The site uses several custom Jekyll plugins (both internal and external):
- Custom internal plugins in `_plugins/internal_plugins.rb`:
  - Email encoding filter for Cloudflare protection
  - PDF embedding with PDF.js
  - Custom Liquid tags for downloads and outbound links
  - Typography filter to prevent runts
  - Emoji shortcodes (`:wave:`) substituted as Unicode characters, replacing `jemoji`
    (which served a PNG per emoji from github.githubassets.com). Aliases come from the
    `gemoji` gem, so the syntax and the full alias set are unchanged; `<code>`, `<pre>`,
    `<tt>`, `<script>` and `<style>` contents are left alone, as are tag attributes.
- External plugins:
  - `jekyll-replace-last` - Replace last occurrence of strings
  - `jekyll-uglify` - JavaScript minification
  - `jekyll-make-sitemap` - Generate sitemaps
  - `jekyll-brotli` - Brotli compression
  - `jekyll-redirect-from` - URL redirects

### Asset Organization
- `_includes/styles/` - SCSS stylesheets with modular organization
- `_includes/scripts/` - JavaScript files including GA, lazy loading, contact forms
- `_includes/fonts/` - Base64 encoded font files for performance
- `assets/images/` - Optimized images with responsive variants
- `bin/` - Build scripts for image processing (WebP conversion, responsive images)

### Key Features
- Responsive image handling with automatic WebP/JPEG srcsets
- Inline critical CSS with SCSS compilation
- Custom email obfuscation for Cloudflare
- PDF.js integration for document embedding
- Lazy loading for images and assets
- Font Awesome icons

### Deployment
- Built and deployed via GitHub Actions (not standard GitHub Pages)
- Source code on `jekyll` branch, compiled site on `main` branch
- Custom domain with Cloudflare DNS

## Working with Content

### Adding Portfolio Items
Create markdown files in `_portfolio-items/` with frontmatter for project details.

### Adding Blog Posts
Create markdown files in `_posts/class/` following Jekyll naming conventions (YYYY-MM-DD-title.md).

### Styling
- Main styles in `_includes/styles/stylish.scss`
- Page-specific styles can be added by setting `tags: css` in frontmatter
- SCSS compilation happens inline during build

### color

Every color the site owns is authored once, as sRGB hex, in `$palette` in
`_includes/styles/_sass/_colors.scss`. It compiles to `--color-*` custom properties on
`:root`, and to a second table under `@media (color-gamut: p3)` where the chromatic
entries carry more chroma than sRGB can hold. **Stylesheets say `var(--color-teal)` and
nothing else** -- no Sass color variables, no hex literals.

To change the color scheme, edit `$palette`. The wide-gamut half is derived by rule, not
by hand, so it follows automatically.

Three rules, because each has a failure that is quiet rather than loud:

- **`colors.declare()` is included exactly once**, by `stylish.scss`. Page stylesheets are
  separate Sass compilations inlined into the same document, so a second include is a
  second copy of the whole table in the HTML.
- **The P3 block must stay inside its `@supports (color: oklch(0 0 0))`.** Custom
  properties accept any tokens, so without the gate an engine lacking `oklch()` stores the
  widened values and fails at *use* -- and an invalid `var()` substitution inherits rather
  than falling back to the sRGB value.
- **`color.adjust()` cannot follow a custom property.** Derive shades into `$palette`
  (see `deep-teal-shade`) rather than reaching for Sass color maths at the call site.

Deliberately left as literals: Wordle's tile colors in `wordle-assistant.scss` and the
vendored syntax theme in `_code-highlight.scss`. Both are other people's palettes, and
widening them would make them wrong.

Full notes in [docs/color.md](docs/color.md): the widening rule and the per-color gains,
why near-neutrals are exempt (it is not only a byte saving -- it keeps `.aberrate` clear of
out-of-range channels on iOS), the `+500 bytes brotli` per page this costs, and `$p3-boost`
for dialling it back or off.

### Fonts

Three faces ship as base64 inside `/assets/css/fonts.css`, which `_layouts/default.html`
links render-blocking. Two hard rules, because both have already broken once:

- **The href must stay a bare `/assets/css/fonts.css`, with no cache-buster.** A Cloudflare
  rule replays a static `Link` header for that exact string as a 103 Early Hint; a `?v=`
  that drifts from it costs a double download.
- **Build each face from its pristine vendor source, never from the previous output.**
  Subsetting an already-subset font ratchets its coverage down on every run.

```bash
bin/font-features.py     # Sunday Club (add --report to write nothing)
bin/font-audit.py        # check the derived swash rules for collisions
bin/subset-sourcesans.py # Source Sans Pro Light (add --report to write nothing)
```

Full notes:

- [docs/fonts.md](docs/fonts.md) -- what is inlined and why, the separate-file trade-off
  with measurements, `font-display: block`, why there are no metric-matched fallback
  `@font-face` rules, and how to read a CLS number on this site.
- [docs/early-hints.md](docs/early-hints.md) -- the `103` setup, the three Cloudflare
  dashboard settings it needs, and how to roll it back. **This couples the repo to the
  dashboard**; read it before touching the href above.
- [docs/html-edge-cache.md](docs/html-edge-cache.md) -- the Cache Rule that makes HTML a
  Cloudflare `HIT` rather than `DYNAMIC`, which cut origin think-time from a 112ms median
  (381ms tail) to 5ms. Also dashboard-coupled, and it means **HTML can be up to 10 minutes
  stale after a deploy**. Measure with the bare `/` URL: query strings are still in the
  cache key, so a `?cb=` buster silently measures the old uncached path.
- [docs/swashes.md](docs/swashes.md) -- how `bin/font-features.py` derives Sunday Club's
  contextual alternates, the six `calt` lookups and their order, and what keeps the arms
  from colliding.

Note `font-feature-settings` on `h1,h2,h3,p,li,th` must name `"calt"` explicitly: the site
sets `letter-spacing` on `html`, and Chrome drops contextual alternates when letter-spacing
is non-zero unless the feature is requested by name.

### Chromatic aberration

`.aberrate` / `.aberrate--hover` / `.aberrate--wander` in
`_includes/styles/_sass/_aberration.scss` split heading text into RGB layers -- always on,
gated on hover, or in continuous motion. See
[docs/chromatic-aberration.md](docs/chromatic-aberration.md).

**The displacement is a product, and each variant supplies one factor**: the authored
`--ca-shift`, times `--ca-gate` (0..1, what `--hover` transitions), times `--ca-wander-x`
(-1..1, what `--wander` animates). `.aberrate` writes that line once and the factors default
to 1 through their `@property` initial values, so the variants compose rather than fight --
`aberrate: "hover wander"`, which the footer icons use, is a walk that runs only while
hovered. A new variant should be a new factor, not another rule writing
`--ca-active-shift`.

Its `--ca-space` branch also tests `(color-gamut: p3)`, and is **unrelated** to the palette
above. That one picks the space the compositor *adds* in so the layers sum back to the text
color; getting it wrong is a visible cast. The palette's branch spends gamut on flat paint
and fixes nothing. Do not change one to match the other.

### Overbright text

`.lift` / `.lift--hover` in `_includes/styles/_sass/_lift.scss` paint text past SDR white
on a display with headroom. It needs nothing of the markup, so it is a bare class --
`[text](url){:.lift}` in kramdown, or a selector in a stylesheet. `.aberrate--lift` is the
same paint wired to the aberration's gate.

The whole feature is `filter: brightness()` on a composited element, because **iOS
composites in extended sRGB and does not clamp out-of-range channels**. There is no image
and no gain map; an out-of-range *color* alone does nothing, since individual paint still
clamps and only the composite escapes.

**`filter` takes the whole element** -- background, border, box-shadow and any image
inside it. Put it on the innermost box holding only the ink you want lifted, and skip it
where there is no such box: an inline link takes it directly, the nav tabs lift their
inner `<span>` because the tab paints a background and a halo, and a link wrapping media
(portfolio screenshots) opts out entirely rather than blowing the photo out. `.bar` is the
deliberate exception, where the background *is* the ink.

**The `@media (dynamic-range: high)` gate is load-bearing, not etiquette.** With no
headroom the multiply only clips -- on `.aberrate--lift` that clips each layer to grey and
*damages* the aberration on the displays that cannot show the glow anyway.

**Body-size glyphs go rough above ~1.4, and that bounds the whole feature.** The multiply
amplifies the antialiasing ramp at a glyph's edge, and the clip at the display's headroom
then holds the core back while the edges keep rising -- letterforms read as furred. It is
the multiply, not the composited layer: `brightness(1)` and `opacity: .999` are both
clean, and `will-change`/`translateZ` do nothing. So `$lift-default` is 1.3 and there is
one value everywhere. There were three -- flat ink, headings, aberrated ink -- and they
converged, because this ceiling binds harder than the reasons to separate them; split them
again if one moves rather than assuming they were always one thing. Note this 1.3 is *not*
the `1 / $ca-own` ceiling that shares its value.

Full notes in [docs/lift.md](docs/lift.md): why the specified gain-map route loses to this
one, what was measured on device (including that no HDR content need be present), why hue
holds only while every channel stays under the display's headroom, and -- if the portable
Chrome-compatible route is ever revisited -- the two silent failures in Apple's ISO
21496-1 encoders.

### Images
- Place source images in `assets/images/`
- Run `./bin/make-images.sh` to generate responsive variants
- Use `{% include modules/image.html image="filename" title="Alt text" %}` for optimized display