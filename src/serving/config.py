from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_env: str = 'devlopment'
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    #
    # class Config:
    #     env_file = '.env'
    #update for version 2 pydantic
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
