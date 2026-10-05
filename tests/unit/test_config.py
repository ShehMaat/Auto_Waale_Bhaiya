from packages.config.settings import Settings


def test_config_loads() -> None:  # type: ignore[no-untyped-def]
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        DATABASE_URL="sqlite://",
        REDIS_URL="redis://",
        S3_ENDPOINT="",
        S3_ACCESS_KEY="",
        S3_SECRET_KEY="",
        S3_BUCKET="",
        JWT_SECRET="test",
    )
    assert settings.APP_ENV == "development"
    assert settings.DATABASE_URL == "sqlite://"
