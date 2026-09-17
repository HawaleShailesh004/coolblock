"""A trivial HTTP listener for the ARQ worker's Render deploy
(docs/adr/0034-*.md's addendum).

Render's free tier has no *Background Worker* service type (confirmed
against the real dashboard, not assumed from the docs) -- only Web
Services, which require something to bind `$PORT` regardless of whether
the process actually serves HTTP traffic, and fail the deploy after a
~5-minute port scan otherwise ("No open ports detected... create a
background worker instead").

`PROCESS_ROLE=worker` genuinely has no HTTP work to do -- the ARQ worker
only pulls jobs from Redis. This stub exists purely to satisfy Render's
port requirement, deliberately as light as possible: stdlib
`http.server`, not FastAPI/uvicorn (the whole reason for the API+worker
split in the first place was memory -- adding the ~270 MB app back in
just to open a port would defeat it). Every request gets a plain 200;
there is nothing here to route or authenticate.
"""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _StubHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler's own naming convention
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ARQ worker running -- no HTTP API here, see /health on the API service.\n")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 -- stdlib's own parameter name
        pass  # silence per-request access logs; the ARQ worker's own logging is what matters here


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), _StubHandler).serve_forever()


if __name__ == "__main__":
    main()
