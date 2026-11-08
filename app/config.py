from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    admin_api_key: str
    tenant_a_api_key: str
    tenant_b_api_key: str


settings = Settings()
