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

# Rebuild the fonts. Each builds from its pristine vendor source; add --report to
# measure and write nothing. See docs/fonts.md and docs/swashes.md.
bin/font-features.py      # Sunday Club's contextual alternates
bin/font-audit.py         # shape a word list, check for colliding swashes
bin/subset-sourcesans.py  # the inlined Source Sans Pro Light
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

Anything with a `docs/` file is documented **there and not also here**. A comment beside
the code says what the line does and, if the line is one someone would be tempted to
simplify away, names the consequence in a sentence -- then deep-links the section:
`// See docs/color.md#the-narrowing-rule.`

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
  - Emoji shortcodes (`:wave:`) substituted as Unicode characters. Aliases come from the
    `gemoji` gem; `<code>`, `<pre>`, `<tt>`, `<script>` and `<style>` contents are left
    alone, as are tag attributes.
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

### Color

Every color is written down once, in OKLCh, in `$palette` in
`_includes/styles/_sass/_colors.scss`, at the chroma it should have on a wide-gamut
display. It compiles to `--color-*` custom properties: an sRGB table on `:root`, and the
authored values under `@media (color-gamut: p3)`. **Stylesheets say `var(--color-teal)`
and nothing else** -- no Sass color variables, no literals. To change the scheme, edit
`$palette`; the sRGB half is derived by rule. Authored colors must sit inside Display P3.

- **`colors.declare()` is included exactly once**, by `stylish.scss`. Page stylesheets are
  separate compilations inlined into the same document, so a second include ships a second
  copy of the whole table.
- Wordle's tile colors and the vendored syntax theme in `_code-highlight.scss` stay as
  literals. They are other people's palettes.

[docs/color.md](docs/color.md).

### Fonts

Three faces ship as base64 inside `/assets/css/fonts.css`, which `_layouts/default.html`
links render-blocking. Two hard rules, both of which have broken once:

- **The href must stay a bare `/assets/css/fonts.css`, with no cache-buster.** A Cloudflare
  rule replays a static `Link` header for that exact string as a 103 Early Hint; a `?v=`
  that drifts from it costs a double download.
- **Build each face from its pristine vendor source, never from the previous output.**
  Subsetting an already-subset font ratchets its coverage down on every run.

`font-feature-settings` on `h1,h2,h3,p,li,th` must name `"calt"` explicitly: the site sets
`letter-spacing` on `html`, and Chrome drops contextual alternates when letter-spacing is
non-zero unless the feature is requested by name.

- [docs/fonts.md](docs/fonts.md) -- what is inlined, the separate-file trade-off,
  `font-display`, and the per-face subsetting notes.
- [docs/swashes.md](docs/swashes.md) -- how `bin/font-features.py` derives Sunday Club's
  contextual alternates.
- [docs/early-hints.md](docs/early-hints.md) and
  [docs/html-edge-cache.md](docs/html-edge-cache.md) -- **both couple this repo to
  Cloudflare dashboard settings**; read them before touching the href above. The edge cache
  also means HTML can be up to 10 minutes stale after a deploy, and that measuring it needs
  the bare `/` URL, since a `?cb=` buster silently measures the uncached path.

### Chromatic aberration

`.aberrate` / `--hover` / `--wander` / `--lift` in
`_includes/styles/_sass/_aberration.scss` split heading text into RGB layers.

**The displacement is a product, and each variant supplies one factor** -- the authored
`--ca-shift`, times `--ca-gate`, times `--ca-wander-x`. The factors default to 1 through
their `@property` initial values, so variants compose rather than fight. A new variant
should be a new factor, not another rule writing `--ca-active-shift`.

Its `--ca-space` branch tests `(color-gamut: p3)` and is **unrelated** to the palette
above: that one picks the space the compositor *adds* in. Do not change one to match the
other.

[docs/chromatic-aberration.md](docs/chromatic-aberration.md).

### Overbright text

`.lift` / `.lift--hover` in `_includes/styles/_sass/_lift.scss` paint text past SDR white
on a display with headroom; `.aberrate--lift` is the same paint wired to the aberration's
gate. It needs nothing of the markup, so it is a bare class -- `[text](url){:.lift}` in
kramdown, or a selector in a stylesheet. The mechanism is `filter: brightness()` on a
composited element, because iOS composites in extended sRGB without clamping.

- **`filter` takes the whole element**, background and borders included. Put it on the
  innermost box holding only the ink you want lifted; a link wrapping a photo opts out.
  `.bar` is the deliberate exception, where the background *is* the ink.
- **The `@media (dynamic-range: high)` gate is load-bearing.** With no headroom the
  multiply only clips, which damages `.aberrate--lift` on the displays that cannot show
  the glow anyway.
- **`$lift-default` is 1.3, everywhere.** The ceiling is antialiasing, not taste: body-size
  glyphs go visibly rough above ~1.4. This 1.3 is *not* the `1 / $ca-own` ceiling that
  shares its value.

[docs/lift.md](docs/lift.md).

### Images
- Place source images in `assets/images/`
- Run `./bin/make-images.sh` to generate responsive variants
- Use `{% include modules/image.html image="filename" title="Alt text" %}` for optimized display