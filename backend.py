import os

import uvicorn

from window_aichat.api.server import app


def _main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("WINDOW_AICHAT_PORT", "8000")))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    uvicorn.run(
        "window_aichat.api.server:app",
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    _main()
