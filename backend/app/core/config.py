from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    jwt_secret: str
    jwt_expiration_minutes: int = 10080  # 7 days
    frontend_url: str = "http://localhost:5173"
    agent_grounding: bool = True  # grounding automático de memória no chat (AGENT_GROUNDING=false desliga)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
