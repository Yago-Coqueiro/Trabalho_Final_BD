from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str
    jwt_secret: str
    jwt_expiration_minutes: int = 10080  # 7 days
    frontend_url: str = "http://localhost:5173"
    agent_grounding: bool = True  # grounding automático de memória no chat (AGENT_GROUNDING=false desliga)
    agent_engine: str = "adk"  # motor do agente: "adk" (Google ADK) ou "legacy" (loop google-genai manual)

    # Observabilidade (OpenTelemetry). Desligado por padrão → provider no-op, zero overhead.
    otel_enabled: bool = False  # OTEL_ENABLED=true liga o tracing distribuído
    otel_service_name: str = "fluxora-backend"
    otel_capture_content: bool = True  # captura conteúdo (msg/args/result) nos spans

    # Destino dos spans: Langfuse Cloud via OTLP/HTTP. Cria-se um projeto em
    # cloud.langfuse.com e colam-se as duas chaves abaixo no .env.
    langfuse_public_key: str = ""  # pk-lf-...
    langfuse_secret_key: str = ""  # sk-lf-...
    langfuse_host: str = "https://cloud.langfuse.com"  # US: https://us.cloud.langfuse.com

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
