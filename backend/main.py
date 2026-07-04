"""Vercel Python runtime entrypoint.

Vercel's zero-config FastAPI detection looks for one of app.py, index.py,
server.py, main.py, wsgi.py, or asgi.py at the project root and expects it to
expose an ASGI `app`. The actual application lives in app/main.py so it can
be run locally the same way as before (`uvicorn app.main:app`); this file
just re-exports it for Vercel.
"""

from app.main import app  # noqa: F401
