"""Pixora Starter -- run the API server with frontend serving."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from pixora.api.main import app  # noqa: E402


def main():
    port = int(os.environ.get("PIXORA_PORT", "8001"))
    print()
    print("  Pixora -- Document Intelligence Platform")
    print(f"  API Docs:   http://localhost:{port}/api/docs")
    print(f"  Frontend:   http://localhost:{port}")
    print(f"  Health:     http://localhost:{port}/api/v1/health")
    print()

    uvicorn.run(
        "pixora.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[os.path.join(os.path.dirname(__file__), "pixora")],
    )


if __name__ == "__main__":
    main()
