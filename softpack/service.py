import uvicorn

from softpack.app import app


def main():
    uvicorn.run(
        "softpack.app:app.router",
        host=app.settings.server.host,
        port=app.settings.server.port,
        reload=True,
        log_level="debug",
    )


if __name__ == "__main__":
    main()
