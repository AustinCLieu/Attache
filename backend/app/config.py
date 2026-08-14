from pydantic_settings import BaseSettings, SettingsConfigDict
# BaseSettings looks for each fields' value from the .env on instance

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    FERNET_KEY: str

    FRONTEND_ORIGIN: str = "http://localhost:3000"

    ANTHROPIC_API_KEY: str = ""
    EMBEDDINGS_API_KEY: str = ""
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_REDIRECT_URI: str = "http://localhost:8000/ms/callback"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()