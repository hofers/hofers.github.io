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

# Rebuild Sunday Club's contextual alternates (see "Swashes" below)
bin/font-features.py            # full build
bin/font-features.py --report   # show the derived rules, write nothing
bin/font-audit.py               # shape a word list and check for colliding swashes

# Re-prune the inlined Source Sans Pro Light (see "Inlined fonts" below)
bin/subset-sourcesans.py            # rebuild
bin/subset-sourcesans.py --report   # measure, write nothing

```

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

### Inlined fonts

`_includes/styles/inline-fonts.scss` inlines three faces as base64 in the critical CSS,
so text paints without a font request. That is 87% of a typical
page's compressed weight, which makes these the only assets on the site where a wasted
kilobyte is worth chasing.

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

### font-display, and why there are no fallback @font-face rules

Inlining the faces removes the *fetch*, but not the two-pass layout. Chrome routes even a
`data:` URL through its remote-font pipeline: it lays the page out once using whatever
local face the stack names, finishes decoding the webfont about 12ms later, and lays out
again. Both passes happen before first paint here -- fonts land around 53ms, FCP is at
97ms -- so no user sees a flash or a jump.

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

#### Reading a CLS number here

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

### Swashes (Sunday Club)
`h1`/`h2` use Sunday Club, which carries swash, titling and stylistic alternates.
`swsh` and `titl` are *single* substitutions and `salt` has one alternate per glyph,
so CSS can only apply them to a whole element -- there is no way to swash one letter
without wrapping it in a `<span>`, which also breaks ligature and `calt` shaping across
the element boundary.

`bin/font-features.py` avoids that by generating contextual (`calt`) rules and compiling
them into the font, so browsers pick the right variant automatically with no markup. It
measures each variant's overhanging ink column by column and only uses it where the
neighbouring letter tucks inside its silhouette. Source of truth is the pristine vendor
`assets/fonts/SundayClub-Bold.woff`; the script regenerates the `.subset.woff2`/`.woff`
and the inlined base64. The generated rules land in `bin/sundayclub.fea` for inspection,
and can be hand-edited then recompiled with `--fea-in`.

Density is controlled by `AUTO_BASES` in the script, since `calt` matches positions and
cannot count swashes per word. It is now empty, meaning every letter is eligible; run with
`--sparse` for the restrained set (capitals plus `f g j k t x y z`).

Every feature the font ships is a candidate (`EXCLUDE_FEATURES` is empty). That matters
because `ss01`-`ss04` are where Sunday Club keeps its intermediate arms: `t` has seven
forms, five reaching left (`alt3` 156, `alt2` 192, `titl` 204, `alt1` 300, `swsh` 340) and
two reaching right (`alt4` 303, `salt` 335). Rules are emitted longest-arm-first and `calt`
is first-match-wins, so each letter gets a ladder -- the longest arm its neighbour can take,
down to the plain glyph. A rule whose context is wholly contained in a higher-priority one
can never fire and is dropped; `t.alt4` goes this way, since `t.salt` clears every
neighbour it does and clears them by more.

#### Six lookups, in order

The rules are split across six `calt` lookups, and the order is the design. Each one sees
what the ones before it drew, so its classes can be written in terms of those glyphs
rather than in terms of what was typed.

| lookup | what it places |
| --- | --- |
| `initial` | a word-initial swash on the first letter of the run |
| `arms` | every variant reaching left -- the long decoration |
| `tails` | word-final flourishes drawn inside their own advance |
| `nubs` | variants reaching only right -- the short ones |
| `fallback` | the vendor's own defensive `calt` rules |
| `restyle` | `ALWAYS_VARIANTS` |

`initial` exists because a backtrack class cannot match what is not there. Every other
position has a glyph before it to name -- including a word after a space, which is why
"Film Festival" used to swash its second `F` and not its first. It is stated as
`ignore sub @anyglyph F';` followed by the unguarded rule, so it fires only where nothing
precedes, and it runs first so the leading letter gets the most decorative form it can
take rather than whatever a one-sided rule offers. Word-initial placement is otherwise
gated on `WORD_INITIAL_MAX_REACH` and on the arm arcing overhead, and the word space
before it is widened by exactly what the arm consumes (`add_word_space_kerns`).

**Arms before nubs** is the substantive ordering. In "Atlantic" the second `t` swings a
340-unit arm back over the `n`, and the price is a plain `a` and a plain `n`, because a
right nub on the `a` would be arcing over that same `n` from the other side. Deriving
everything in one pass made that a race the nub won by sitting earlier in the word;
deriving arms first makes it a decision, and 340 units of swash beats 86.

The split pays again in precision. A rule's lookahead cannot see lookups that have not run
yet, so a single pass has to assume the letter ahead may still take any shape it has --
which is why plain `a` was refused after `Z.swsh` on account of `a.titl`, a form that only
ever appears at the end of a word. By the time `nubs` runs, `arms` and `tails` have both
had their say, so its lookahead names the glyph that will actually be drawn.

#### What keeps arms from colliding

- **Both sides are tested against what will actually be drawn.** `calt` walks the run once,
  left to right, so a backtrack class must name variant glyphs -- write it in plain letters
  and a swash can never follow a swash ("Atlantic" loses the arm on its `t` because the `A`
  turned into `A.swsh` first). Lookahead has the opposite problem: a letter qualifies on the
  right only if *every* form still open to it clears the arm.
- **An arm needs a short letter under it** (`Geometry.obstructs`, `ARC_HEADROOM`). Clearance
  is not the whole question. `l.swsh` clears a preceding `t` by 32 units and a preceding `H`
  by 21, which passes `PROTRUSION_LIMIT` -- but the arm runs level along the top of that
  extender for 22 columns, and two near-parallel strokes a fiftieth of an em apart read as
  one tangled stroke rather than an arc. This is what "Atlantic" and "Zarathustra" were
  doing: the `l` and the `h` each swung a 270-unit arm back over the `t` in front of it,
  threading between its ascender and the cap line. What separates the pairs that work is not
  how much room is left but what is beneath the arm, and this face leaves a clean band to cut
  in -- x-height letters top out at 366 and the next thing up is `t` at 435, capitals at 445,
  ascenders at 504. So an arm's own columns must find nothing taller than
  `x_top + ARC_HEADROOM`, and an under-sweep nothing deeper than `x_bottom - ARC_HEADROOM`.
  The band is measured off the outlines because OS/2 cannot be trusted here: Sunday Club
  reports `sxHeight` 500, nearer its ascender than the top of any x-height letter it draws.
  Asked of `arm_ink` only -- the innermost columns of an overhang hold the variant's own
  body, and the letter it replaced stood beside that same extender quite happily. It costs
  almost nothing in density: the long arms keep every x-height neighbour they had, including
  the tight ones (`t.swsh` over `v` at 22 units), and overall decoration falls 59% to 58%.
- **`Geometry.covers` keeps an arm inside the one letter it arcs over**, to within
  `COVER_SLACK`, which is one column -- the resolution the envelope is measured at, and no
  more. At 40 units of slack an arm reaches far enough past its neighbour to land on the
  ascender of the letter after it, which was this script's largest source of collisions.
- **A letter under an arm keeps the shape the arm was measured against** (`reshape_guards`).
  An arm and a variant in the letter beside it normally cannot collide -- `covers` puts the
  arm inside that letter's box and the variant's decoration outside it. What breaks that is
  a variant which changes the box: `r.swsh` trades 150 units of advance for its arm, so an
  `r` already arced over by a following `t.swsh` shrinks under it, dragging the `t` left and
  running its arm off the far side into the letter beyond. Every long-range collision the
  audit found came from this. It cuts both ways -- `a.swsh` is 20 units narrower than `a`,
  enough to slide the `a` out from under `Z.swsh`'s tail. Stated as an `ignore` in the later
  lookup rather than by striking those letters out of the arms' classes, because the arm is
  the decoration worth keeping.
- **A letter may be arced over from one side only** (`one_side_guards`) -- a right arm from
  two positions back meeting a left arm from here, inside the letter between them. Neither
  rule can see the other, so it is stated separately over two positions of backtrack. Not as
  a blanket ban, though: the two arms are compared as vertical extents and only the pairs
  that actually meet are suppressed. In "Zarathustra" the `u` drops a tail below the baseline
  under the `s` while the `t` swings an arm over the top of it, and reading that as a
  collision cost two swashes. `@rightarm` is defined by geometry, not by the rule set, so it
  also catches `f`, which is simply drawn with its hook 67 units past its advance.
- **An `ignore` rather than a narrower class on each rule**, because a two-position class
  cannot match where only one glyph precedes -- the second letter of a heading -- and would
  drop the swash there.

Two measurements underpin all of this and are worth knowing:

- `Geometry.arm_ink` is the overhang with its innermost `ARM_MARGIN` dropped. Right at the
  advance the column envelope stops telling arm from letter: a variant drawn narrower than
  the letter it replaces pushes its own body past the cut, and `Z.swsh`'s bar terminal ends
  up sharing one column with a swash diving 133 below the baseline. Read as an arm, that
  column says `Z.swsh` swallows its neighbour whole. Everything asking *where the arm points*
  works from `arm_ink`; the clearance measurement still uses the full overhang, since every
  unit of ink outside the box has a neighbour under it.
- `Geometry.orientation` is judged at the tip, over the outer third of the arm's columns.
  The columns nearest the stem hold the letter itself, so averaging over the whole arm reads
  `A.swsh` -- whose curl sits at 300 but whose own left leg shares its columns -- as sweeping
  under, which cost it every neighbour it had and the word-initial placement the face draws
  it for.

#### Variants with nothing to overhang

Variants whose flourish stays inside the advance box have no neighbour to clear, so the
overhang test discards them. Two later lookups pick those up, both running after the arms so
a letter that already earned a swash keeps it:

- `tails` -- word-final only, for variants that decorate inside their own advance, via
  `MIN_FLOURISH`, plus anything named in `FINAL_VARIANTS`. Two qualify: `s.swsh`, a tail
  dropping 64 below the baseline, and `a.titl`, a terminal sweep 164 past plain `a`'s right
  edge with the advance widened 152 to hold it. Neither overhangs anything, so neither has a
  context to derive; the end of a word is the one placement the geometry cannot argue with,
  and it fires at most once per word. "No letter follows" is stated as an `ignore`, since a
  lookahead class cannot match the end of a run, and `@wordchar` includes variant and
  ligature glyphs because `arms` may already have replaced the following letter. It runs
  *before* `nubs` so that the nubs' lookahead can name the flourished glyph outright.
- `restyle` -- unconditional, for `ALWAYS_VARIANTS`. Holds three glyphs, for two reasons.
  `e.swsh` and `i.salt` are not flourishes. `e.swsh` has the same advance and silhouette as
  plain `e` to within 1 unit/em, but with the bar detached from the bowl so the aperture
  opens; `i.salt` is closer still -- same advance, same bounding box to the unit, differing
  only in that the tittle joins the stem into one contour instead of floating free. Both are
  simply the letterforms the site wants, and the column envelope is a silhouette test that
  cannot see interior differences like these. `C.swsh` is the opposite -- unmistakably a
  decorated letter, its spiral terminal drawn wholly inside the advance, so the fit test
  scores it 0 on every measure and has nothing to say about where it belongs. A capital in a
  heading is about one per word and almost always leads it, which is the classic place for a
  swash, so it is used everywhere. In every case the vendor's kern classes already cover the
  variant, so spacing is unaffected. Note `eacute` and friends have no such variant and keep
  the closed bowl.

#### Auditing

`bin/font-audit.py` is what verifies all of this, and is worth re-running after any change
to the rules. It shapes a word list with the *built* font and re-applies both fit tests to
every glyph an arm passes over, which is the only way to see the difference between what the
rules assumed and what the shaper draws. On a 5,000-word sample the current rules leave 0.2%
of words with a graze, all of them at two positions' distance, for 67% of glyphs carrying a
variant. Anything above 1% fails the run. Every remaining failure is an arm that cleared its
neighbour and landed on the extender of the letter beyond -- the one thing a single position
of backtrack cannot see. For scale, the same audit against the build before `ARC_HEADROOM`
reports 10.9%, nearly all of it one position away.

`font-feature-settings` on `h1,h2,h3,p,li,th` must name `"calt"` explicitly: the site sets
`letter-spacing` on `html`, and Chrome drops contextual alternates when letter-spacing is
non-zero unless the feature is requested by name.

The `.salt`, `.swsh` and `.titl` classes remain for deliberate one-off overrides.

### Images
- Place source images in `assets/images/`
- Run `./bin/make-images.sh` to generate responsive variants
- Use `{% include modules/image.html image="filename" title="Alt text" %}` for optimized display