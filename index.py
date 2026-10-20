# Entrypoint for Vercel: it looks for a FastAPI instance named `app` in this file.
from app.main import app  # noqa: F401
