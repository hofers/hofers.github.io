# Caching the HTML at Cloudflare's edge

Every page view used to be a full trip from the Cloudflare edge to the GitHub Pages origin,
because `cf-cache-status` on HTML was `DYNAMIC` -- Cloudflare does not cache HTML by default.
A Cache Rule makes it `HIT` instead. Applied 2026-08-28.

This site is entirely static: no server-side logic, email obfuscation happens at build time,
GA and the contact form are client-side. Nothing about the HTML needs to be dynamic, so the
only real cost is staleness, bounded below.

## The rule

Caching -> Cache Rules, matching on request fields (Cache Rules cannot see the response, so
this cannot key off `content_type`):

```
(http.host eq "seanhofer.com"
 and not starts_with(http.request.uri.path, "/assets/")
 and not starts_with(http.request.uri.path, "/cdn-cgi/"))
```

| Setting | Value |
| --- | --- |
| Cache eligibility | Eligible for cache |
| Edge TTL | **Use cache-control header if present, bypass cache if not** |
| Browser TTL | Respect origin TTL |

Both exclusions are load-bearing. `/assets/` keeps [early-hints.md](early-hints.md)'s Rule A
on `fonts.css` untouched. `/cdn-cgi/` must never be cached -- Cloudflare's own email-protection
decoder and RUM beacon live there.

Two things follow from the TTL choice, and both were the point of choosing it:

- **No TTL is hardcoded in the dashboard.** GitHub Pages sends `max-age=600` on HTML, so the
  edge inherits 10 minutes and the number stays owned by the origin.
- **"bypass cache if not" over "Cloudflare's default TTL for the response status".** The only
  response under this rule lacking `cache-control` is the 404, which now shows `BYPASS`. The
  other option would have cached 404s at a TTL nobody chose, so a transient origin hiccup
  serving a 404 for a real URL would pin at the edge.

The rule also catches `/robots.txt` and `/redirects.json`. Both are static; harmless.

## What it bought

Measured from a PDX/DEN/DFW colo, before and after, on the real `/` URL:

| | before | after |
| --- | --- | --- |
| think-time (`103`->`200`) | median 112ms, **max 381ms** | median 5ms, max 10ms |
| HTML fully downloaded (browser) | median ~399ms | median ~230ms |
| FCP (cold profile, n=10) | median 500ms | median 448ms |

FCP moves less than TTFB does because it is gated by the 40KB `fonts.css` download, which
this change does not touch. Killing the 381ms tail matters more than the median.

**Measure with the bare `/` URL.** Query strings are still part of the cache key, so a
`?cb=123` cache-buster forces a `MISS` every time and silently measures the old behaviour.

## Consequences

**HTML can be up to 10 minutes stale after a deploy.** The workflow pushes to `main`, GitHub
Pages picks it up, and the edge does not notice until the TTL expires. For an urgent deploy,
purge from the dashboard (Caching -> Configuration -> Purge Cache). An API purge step in
`.github/workflows/jekyll.yml` was considered and deferred: it needs a `CLOUDFLARE_ZONE_ID`
and a scoped `CLOUDFLARE_API_TOKEN` secret, and a silently failing purge serves stale HTML
for a full TTL. The manual step is the better trade at this deploy frequency.

A cache key cannot solve this. Cache keys are built from the *request*, and a visitor's
request for `/` is byte-identical before and after a deploy -- there is no origin- or
content-derived component to include. Versioned URLs work for subresources because the href
is under our control; the HTML document's URL is not.

**Each colo caches independently.** Sequential requests from one machine landed on PDX, DEN
and DFW, and each had to miss once before hitting. With a 600s TTL and low traffic, a colo
that sees fewer than one request per 10 minutes will miss more often than not. Tiered Cache
would make a miss cost an upper-tier fetch instead of a full origin trip; not measured, and
worth checking against the current plan before enabling.

**Query strings are still in the cache key.** Ignoring them would fold `?utm_source=...` and
`?fbclid=...` variants into one entry and raise the hit rate; the HTML is byte-identical
across query strings (verified by hash). Deferred deliberately, to keep one variable moving
at a time -- and because it would break `?cb=` cache-busting for measurement.

## Effect on Early Hints

It largely retires the win documented in [early-hints.md](early-hints.md). With think-time at
5ms there is almost nothing left to overlap. From the local control (real `103`, real bytes,
`jobs 2/1` verified):

| | saving from the `103` |
| --- | --- |
| full origin trip, unthrottled | 46ms |
| full origin trip, 1.6 Mbps | 101ms |
| edge-cached HTML, unthrottled | **19ms** |
| edge-cached HTML, 1.6 Mbps | **17ms** |

Keep it anyway: it costs nothing, it is still positive, and on a colo miss the old numbers
apply again. It is now insurance for cache misses rather than the main event.
