from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    otp_provider_api_key: str
    use_real_otp: bool = False

    class Config:
        env_file = ".env"

settings = Settings()