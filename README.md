# cdcollection-python

A web catalogue for an audio CD collection, backed by [PocketBase](https://pocketbase.io/).
Browse the collection, search it, and add or remove discs from the browser.

A single-file Flask app: the UI is a Tailwind template rendered server-side, so there is no build
step and no JavaScript toolchain.

## Running it locally

```bash
pip install -r requirements.txt
```

```bash
python app.py
```

It listens on port 5000 and expects a PocketBase instance holding a collection named `audiocd`.

## Configuration

All settings come from the environment; none are required to start.

| Variable | Purpose | Default |
| --- | --- | --- |
| `POCKETBASE_URL` | Where PocketBase lives | `http://127.0.0.1:8090` |
| `FLASK_SECRET_KEY` | Signs the session cookie used for flash messages | random per process |
| `MOCK_AUTH_USER` | Forces a signed-in username, for local development | unset |

**`MOCK_AUTH_USER` bypasses authentication entirely.** It exists so the app is usable without a
proxy in front of it. Never set it in a deployed environment.

Leaving `FLASK_SECRET_KEY` unset generates a fresh key at startup, which is safe but invalidates
flash messages across restarts. Set it if that matters.

## Authentication

The app does not authenticate anyone itself. It trusts the `Remote-User`, `X-Webauth-User` and
`X-Forwarded-User` headers, which is what a forward-auth proxy such as Authelia sets. Reads are
open; adding and deleting require one of those headers to be present.

This means **the app must not be exposed directly.** Anything that can reach it can set those
headers itself and write to the collection. It belongs behind a proxy that strips client-supplied
copies of them.

## Container

The `Dockerfile` builds a gunicorn image. Images are published to
`ghcr.io/zzzaspany/cdcollection-python` by the build workflow on every push to `main`.

`cdcolletion-python.container` is the Quadlet unit used to run it under rootless Podman.

## Licence

MIT — see [LICENSE](LICENSE).
