from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_env: str = 'devlopment'
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int


    class Config:
        env_file = '.env'

settings = Settings()
