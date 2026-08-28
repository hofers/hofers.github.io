# Early Hints

How `/assets/css/fonts.css` is preloaded during origin think-time, and the Cloudflare
dashboard configuration it depends on. Background in [fonts.md](fonts.md).

> **Superseded in part, 2026-08-28.** The premise below -- that HTML is `cf-cache-status:
> DYNAMIC` and every view is a full origin trip -- stopped being true when the HTML was
> edge-cached; see [html-edge-cache.md](html-edge-cache.md). Think-time fell from a median
> of 112ms to 5ms, and with it the value of the hint, from 46-101ms to 17-19ms. The `103` is
> still configured and still worth keeping as insurance for a colo miss, where the original
> numbers apply again. Everything below remains accurate for the cache-miss path.

The cold-start RTT measured in [fonts.md](fonts.md) is dead air, not bandwidth: the HTML was
`cf-cache-status: DYNAMIC`, so every page view was a full trip to the GitHub Pages origin
(TTFB 310-540ms) while `fonts.css` sits edge-cacheable at ~110ms. A `103 Early Hints`
response lets the browser start that download *during* origin think-time. Measured against a
real HTTP/2 server emitting a real `103` (cold first page, origin 400ms / edge 110ms, median
of 7-9 runs):

| | inline (before) | external, no hint | **+ 103** |
| --- | --- | --- | --- |
| unthrottled | 484ms | 584ms | **484ms** |
| 1.6 Mbps | 676ms | 796ms | **488ms** |
| 0.8 Mbps | 924ms | 1040ms | **520ms** |

On a constrained connection it does not merely cancel the cold-start cost -- it beats the
old inline build by 188-404ms, because the 40KB downloads in parallel with origin
think-time. Inlining can never do that; those bytes are trapped inside the slow response.

### What bounds the saving

Read that table with its conditions in mind, because it is the good case. All the hint buys
is the *overlap* between two things that would otherwise be serialised, so:

> saving = min(origin think-time, cost of fetching `fonts.css`)

Whichever is smaller is the binding constraint, and the other one has slack. That single
line reconciles every number here.

The 0.8 Mbps row is think-time-bound: 40KB takes ~400ms to pull down, think-time is ~400ms,
and the hint recovers nearly all of it. A desktop visitor on a fat pipe is the other case
entirely -- the CSS costs only ~88ms uncontended, so that is the ceiling no matter how slow
the origin is. Measured on the live site against both a within-run control (real domain,
n=3 uncontended, 98-168ms) and a clean local control (real `103`, real bytes, think-time
calibrated to production), a fast connection saves **60-130ms**, not 188-404ms.

Both are worth having and neither is the headline on its own. The optimisation pays out
most where it is needed most, which is the shape you want, but do not quote the constrained
figure for a desktop visitor.

One trap specific to re-deriving this. The preload is slower than a normal fetch -- 177ms
median against 88ms -- because it is competing with the HTML for the same connection. Using
the preload's own duration as the stand-in for a no-hint fetch therefore inflates the
apparent saving by roughly 2x. Measure the no-hint cost from a fetch that has the connection
to itself.

It is entirely dashboard configuration, in three parts:

1. **Speed -> Optimization -> Content Optimization -> Early Hints**: on.
2. **Rule A**, Transform Rules -> Modify Response Header, when
   `http.request.uri.path eq "/assets/css/fonts.css"`, set static `Cache-Control` to
   `max-age=86400, stale-while-revalidate=604800`. Note a zone-level Browser Cache TTL is
   also in play (it rewrites GitHub Pages' native `600` to `172800`); if it wins, set it to
   "Respect Existing Headers" or scope a Cache Rule to this path.
3. **Rule B**, Modify Response Header on HTML responses
   (`http.response.content_type.media_type eq "text/html"`), set static `Link` to
   `</assets/css/fonts.css>; rel=preload; as=style`. Cloudflare harvests this from the
   response and replays it as the `103` on subsequent requests.

**This couples the repo to the dashboard.** The URL in Rule B is a literal string, so
`fonts.css` must keep a stable, unversioned href -- reintroducing a cache-buster without
editing Rule B causes a double download (measured 2.00 fetches/load, zero benefit).

Accepted trade-offs, chosen rather than incidental: a font change takes up to a day to
reach returning visitors, and Safari ignores `stale-while-revalidate`
([WebKit #201461](https://bugs.webkit.org/show_bug.cgi?id=201461)) so a returning Safari
visitor pays one blocking ~110ms edge revalidation per day. Safari 17 supports only
`preconnect` in `103`, not `preload`, so it gets none of the upside -- a real asymmetry,
a small Safari cost for a Chrome/Firefox/Edge benefit.

## Verifying it still works

The Network panel cannot show you this, and reading it naively says the hint is doing
nothing. The `103` preload is issued by the browser process before the renderer's network
domain is attached, so it never appears in the waterfall. The single `fonts.css` row you
*do* see is the parser reaching the `<link>` on line 8 of `_layouts/default.html` and
picking the preload back up -- which is why it looks like it starts ~10ms either side of
the HTML finishing. That is the reuse, not the fetch.

**Uncheck "Disable cache" before believing anything the panel tells you.** That checkbox is
CDP `Network.setCacheDisabled`, which permits the preload but forbids reusing it, so the
parser re-downloads the whole 40KB and the row shows a full ~85ms of real network time.
Measured on the live site, same page, same browser, only the checkbox differing:

| | preload (invisible) | the row you see |
| --- | --- | --- |
| Disable cache **off** | 60-73ms | **2ms** |
| Disable cache **on** | 63-89ms | **53-73ms** |

So: incognito, cache enabled, one load. A ~2ms row for a 40KB file on a cold profile is the
hint working. For the preload fetch itself, `chrome://net-export` is the only view that has
it; `URL_REQUEST_START_JOB` for `fonts.css` appears twice per load, and the first one is the
`103`.

That said, "Disable cache" *on* is a usable control if you want one without standing up a
server, because it puts both arms in a single load: the preload is the hint, and job 2 is a
real no-hint fetch issued at HTML-done. The `no-cache` request header it adds does not cost
you an edge miss (`cf-cache-status: HIT` either way). The catch is contention -- discard any
run where job 2 starts before the preload finishes, or the discarded preload is stealing
bandwidth from your control. That was 7 runs in 10.

Two further traps. The first: Chrome silently ignores Early Hints over a connection with
certificate errors, which is what makes a local control server awkward to build -- a
self-signed cert quietly disables the very thing being measured. The way through is
`--ignore-certificate-errors-spki-list=<base64 sha256 of the SPKI>`, which suppresses the
error without flagging the connection, so the `103` is still honoured. Whatever you build,
confirm the control is real by counting `URL_REQUEST_START_JOB` entries for `fonts.css`:
two with the hint, one without. If the control shows two, it is not a control.

The second: a warm origin shrinks the prize. GitHub Pages answering `x-proxy-cache: HIT`
cuts the `103`-to-`200` gap to ~100ms, well under the 310-540ms the table above was built
on, so a fast run is not evidence of a broken hint.

## The preload does not hold up the HTML

They are independent streams multiplexed on one HTTP/2 connection; the navigation is never
made to wait on the preload. Across 8 cold loads the HTML's last byte landed *mid-CSS-stream*
in 3 of them.

When the parser gets there first, it does not start a second download -- it attaches to the
in-flight response and pays only the remainder, 49-65ms in those three runs instead of 2ms.
The tell is that the two jobs end on the same millisecond (1415/1415, 353/353, 343/343):
one response, two readers. The only real interaction is that 40KB of CSS shares bandwidth
with a much smaller HTML document, which is the trade the whole scheme is making on purpose.

To roll back, delete both rules and restore the `FontCacheKey` digest scheme.
