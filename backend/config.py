from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    database_url_sync: str
    redis_url: str
    gemini_api_key: str
    llm_model_generation: str = "gemini-3.1-flash-lite"
    llm_model_scoring: str = "gemini-3.1-flash-lite"
    llm_rpm_limit: int = 10
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.2
    sandbox_pool_size: int = 4
    eval_timeout_ms: int = 30000
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()