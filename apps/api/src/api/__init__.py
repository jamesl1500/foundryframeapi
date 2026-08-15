def main() -> None:
    import uvicorn

    from api.core.config import get_api_settings

    settings = get_api_settings()
    uvicorn.run(
        "api.main:app", host="0.0.0.0", port=8000, reload=settings.environment == "local"  # noqa: S104
    )
