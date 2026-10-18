"""Create server-only Compose settings without printing or overwriting secrets."""
import os
import secrets
from pathlib import Path

path = Path(__file__).resolve().parent.parent / ".env"
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env already exists; kept existing server settings.")
with os.fdopen(fd, "w") as stream:
    stream.write(
        f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}\n"
        "POKER_AGENT_MODE=strategy\n"
        "HTTP_PORT=8080\n"
        "BIND_ADDRESS=0.0.0.0\n"
        "FRONTEND_URL=http://localhost:8080\n"
    )
print("Created private .env. Set FRONTEND_URL to the public URL before starting.")
