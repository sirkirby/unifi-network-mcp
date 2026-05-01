# Vendored admin UI assets

These files are checked in so the unifi-api admin UI has zero CDN runtime dependency. Refresh by re-running the curl commands below.

| File | Version | Source |
|---|---|---|
| `pico.min.css` | 2.0.6 | https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css |
| `htmx.min.js` | 2.0.4 | https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js |
| `htmx-sse.min.js` | 2.2.2 | https://unpkg.com/htmx-ext-sse@2.2.2/sse.js |

## Refresh

```sh
cd apps/api/src/unifi_api/static/admin
curl -sSL "https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css" -o pico.min.css
curl -sSL "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js" -o htmx.min.js
curl -sSL "https://unpkg.com/htmx-ext-sse@2.2.2/sse.js" -o htmx-sse.min.js
```

Bump the versions here and in this README. Run the apps/api tests; the admin UI tests assert these files are served at `/admin/static/<name>` so any rename will break them loudly.
