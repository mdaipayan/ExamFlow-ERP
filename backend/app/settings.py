import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    environment: str = os.getenv("ENVIRONMENT", "staging")
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    bootstrap_key: str = os.getenv("BOOTSTRAP_KEY", "")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30


settings = Settings()

if settings.environment == "production" and len(settings.jwt_secret) < 32:
    raise RuntimeError("Production JWT_SECRET must be at least 32 characters.")

if settings.environment == "production" and len(settings.bootstrap_key) < 24:
    raise RuntimeError("Production BOOTSTRAP_KEY must be at least 24 characters.")
