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
`docs/html-edge-cache.md`, `docs/swashes.md`, `docs/chromatic-aberration.md`.

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

`.aberrate` / `.aberrate--hover` in `_includes/styles/_sass/_aberration.scss` split heading
text into RGB layers. See [docs/chromatic-aberration.md](docs/chromatic-aberration.md).

### Images
- Place source images in `assets/images/`
- Run `./bin/make-images.sh` to generate responsive variants
- Use `{% include modules/image.html image="filename" title="Alt text" %}` for optimized display