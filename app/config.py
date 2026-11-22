from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./esante.db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Compte admin créé par `python -m app.seed` (facultatif)
    ADMIN_IDENTIFIANT: str = ""
    ADMIN_NOM: str = "Administrateur"
    ADMIN_MOTDEPASSE: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()