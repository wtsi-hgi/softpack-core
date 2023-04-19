import uvicorn


def main():
    uvicorn.run(
        "softpack.app:app.router",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        )

if __name__ == "__main__":
    main()


