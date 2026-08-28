# Early Hints

How `/assets/css/fonts.css` is preloaded during origin think-time, and the Cloudflare
dashboard configuration it depends on. Background in [fonts.md](fonts.md).

The cold-start RTT measured in [fonts.md](fonts.md) is dead air, not bandwidth: the HTML is
`cf-cache-status: DYNAMIC`, so every page view is a full trip to the GitHub Pages origin
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

Two traps if this is ever re-measured: Chrome silently ignores Early Hints over a
connection with certificate errors, and CDP `Network.setCacheDisabled` breaks preload
reuse, which shows up as a phantom 2x download.

To roll back, delete both rules and restore the `FontCacheKey` digest scheme.
